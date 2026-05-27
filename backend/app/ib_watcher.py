"""IB Gateway price subscription + alert trigger.

Maintains one ib_insync IB() connection. Subscribes streaming quotes for every distinct
symbol with an active alert, watches for price crosses, fires Claude when triggered.

If IB Gateway isn't reachable at startup, we silently disable IB and fall back to
periodic yfinance polling (slow but at least functional for dev). The MCP `price-alert`
tool still works — the alert just won't fire until IB is up.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import alerts_db, chat_log, event_bus, quote_cache
from .claude_runner import run_claude
from .config import IB_CLIENT_ID, IB_HOST, IB_PORT

log = logging.getLogger(__name__)

_ib: Any = None
_subscribed: dict[str, Any] = {}  # symbol -> Ticker
_last_price: dict[str, float] = {}
_poll_task: asyncio.Task | None = None
_loop_running = False


def _provider(symbol: str) -> float | None:
    return _last_price.get(symbol.upper())


async def start() -> None:
    global _ib, _loop_running, _poll_task
    quote_cache.set_ib_provider(_provider)
    await alerts_db.init()

    # ib_insync 内部用 asyncio.get_event_loop()，需要确保它拿到的是
    # uvicorn 当前正在运行的 loop，而不是主线程的旧 BaseSelectorEventLoop
    loop = asyncio.get_running_loop()
    asyncio.set_event_loop(loop)

    try:
        from ib_insync import IB
    except ImportError:
        log.warning("ib_insync not installed; IB price alerts disabled")
        return

    _ib = IB()
    try:
        await _ib.connectAsync(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=4)
        log.info("IB connected at %s:%s", IB_HOST, IB_PORT)
        # 3 = delayed data（无需实时行情订阅）；1 = live（需要订阅）
        # 如果有实时行情权限可改为 1
        _ib.reqMarketDataType(3)
        log.info("market data type set to DELAYED (3)")
        _ib.pendingTickersEvent += _on_tickers
    except Exception as e:
        log.warning("IB connect failed (%s); price alerts use yfinance fallback poller", e)
        _ib = None

    await reconcile()
    # 不管 IB 是否连接，都启动 yfinance 补充轮询
    # IB 连接时：yfinance 用于盘前/盘后（IB delayed data 在非正规时段无 tick）
    # IB 断开时：yfinance 作为唯一数据源
    _loop_running = True
    _poll_task = asyncio.create_task(_fallback_poll_loop())


async def stop() -> None:
    global _loop_running
    _loop_running = False
    if _poll_task:
        _poll_task.cancel()
    if _ib is not None:
        try:
            _ib.disconnect()
        except Exception:
            pass


async def reconcile() -> None:
    """Diff active alerts vs current IB subscriptions; sub/unsub as needed."""
    rows = await alerts_db.list_active()
    wanted = {r["symbol"].upper() for r in rows}
    if _ib is None:
        return
    from ib_insync import Stock
    for sym in wanted - set(_subscribed.keys()):
        try:
            contract = Stock(sym, "SMART", "USD")
            await _ib.qualifyContractsAsync(contract)
            ticker = _ib.reqMktData(contract, "", False, False)
            _subscribed[sym] = ticker
            log.info("subscribed IB market data: %s", sym)
        except Exception as e:
            log.warning("subscribe %s failed: %s", sym, e)
    for sym in set(_subscribed.keys()) - wanted:
        try:
            _ib.cancelMktData(_subscribed[sym].contract)
        except Exception:
            pass
        _subscribed.pop(sym, None)


def _nan(v) -> bool:
    try:
        return v != v  # NaN check
    except Exception:
        return True


def _on_tickers(tickers) -> None:
    for t in tickers:
        sym = (t.contract.symbol or "").upper()
        # 优先: last → close（非交易时间 last=NaN，close 是前一日收盘）
        price = None
        for candidate in (t.last, t.close):
            if not _nan(candidate):
                try:
                    p = float(candidate)
                    if p > 0:
                        price = p
                        break
                except Exception:
                    continue
        if price is None:
            continue
        old = _last_price.get(sym)
        _last_price[sym] = price
        if old != price:
            log.debug("IB tick %s: %.4f", sym, price)
        asyncio.create_task(_check_alerts(sym, price))


async def _check_alerts(symbol: str, price: float) -> None:
    rows = await alerts_db.list_active()
    for r in rows:
        if r["symbol"].upper() != symbol:
            continue
        d = r["direction"]
        if (d == "above" and price >= r["target"]) or (d == "below" and price <= r["target"]):
            row = await alerts_db.mark_fired(r["id"], price)
            if row:
                await _fire_alert(row)


async def _fire_alert(row: dict[str, Any]) -> None:
    sid = row["sid"]
    chat_log.append(sid, {
        "role": "system", "kind": "alert",
        "alert_id": row["id"], "symbol": row["symbol"],
        "target": row["target"], "direction": row["direction"],
        "fired_price": row.get("fired_price"), "note": row.get("note", ""),
    })
    event_bus.publish(sid, {"type": "alert_fired", "alert": row})
    asyncio.create_task(run_claude(sid, "alert", {
        "symbol": row["symbol"], "target": row["target"], "dir": row["direction"],
        "alert_id": row["id"],
    }))
    await reconcile()


def _yf_best_price(sym: str) -> float | None:
    """获取最优价格：盘前/盘后 > 正规市场价，确保告警在延伸交易时段也能触发。"""
    import yfinance as yf
    t = yf.Ticker(sym)
    info = t.info
    # 优先级：preMarketPrice > postMarketPrice > regularMarketPrice > lastPrice
    for key in ("preMarketPrice", "postMarketPrice", "regularMarketPrice"):
        v = info.get(key)
        if v and float(v) > 0:
            state = info.get("marketState", "")
            log.debug("yf %s price=%.4f (%s, marketState=%s)", sym, float(v), key, state)
            return float(v)
    fast = t.fast_info
    v = fast.get("lastPrice") or fast.get("last_price")
    return float(v) if v else None


async def _fallback_poll_loop() -> None:
    """当 IB 离线时，每 30s 用 yfinance 轮询；盘前/盘后价格也能触发告警。"""
    log.info("starting yfinance fallback poll loop (30s)")
    while _loop_running:
        try:
            rows = await alerts_db.list_active()
            symbols = sorted({r["symbol"].upper() for r in rows})
            loop = asyncio.get_running_loop()
            for sym in symbols:
                try:
                    # yfinance 是同步 IO，放到线程池避免阻塞事件循环
                    price = await loop.run_in_executor(None, _yf_best_price, sym)
                    if price:
                        log.info("yfinance poll %s = %.4f", sym, price)
                        _last_price[sym] = price
                        await _check_alerts(sym, price)
                except Exception:
                    continue
        except Exception:
            pass
        await asyncio.sleep(30)
