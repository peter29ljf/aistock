#!/usr/bin/env python3
"""MCP: yfinance K-line download + technical indicators + real-time quote."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from _common import aistock_root

from app.market_data import MarketDataService

mcp = FastMCP("yfinance-tools")

_svc = MarketDataService(aistock_root() / "data" / "kline_cache")


_PERIOD_LOOKBACK = {
    "5d": 5, "1mo": 30, "3mo": 92, "6mo": 183,
    "1y": 365, "2y": 730, "5y": 1825, "10y": 3650, "ytd": 365,
}


def _resolve_dates(start: str | None, end: str | None, period: str | None) -> tuple[date, date]:
    end_d = date.fromisoformat(end) if end else date.today()
    if start:
        start_d = date.fromisoformat(start)
    elif period and period in _PERIOD_LOOKBACK:
        start_d = end_d - timedelta(days=_PERIOD_LOOKBACK[period])
    else:
        start_d = end_d - timedelta(days=365)
    return start_d, end_d


@mcp.tool()
def get_stock_quote(symbols: list[str]) -> dict:
    """Get current stock price supporting full session (pre-market / regular / post-market).
    Returns latest price, market state, and per-session change info for each symbol.
    Use this instead of tiger get_stock_quote — works 24h and needs no broker subscription.
    """
    results = []
    for sym in symbols:
        sym = sym.upper()
        try:
            info = yf.Ticker(sym).info
            market_state = info.get("marketState", "UNKNOWN")

            pre = info.get("preMarketPrice")
            post = info.get("postMarketPrice")
            regular = info.get("regularMarketPrice")

            # Pick most relevant price for the current session
            if market_state in ("PRE", "PREPRE") and pre and float(pre) > 0:
                price = float(pre)
                price_source = "pre_market"
            elif market_state in ("POST", "POSTPOST") and post and float(post) > 0:
                price = float(post)
                price_source = "post_market"
            elif regular and float(regular) > 0:
                price = float(regular)
                price_source = "regular"
            else:
                # fallback: any non-zero price
                price, price_source = None, None
                for v, src in ((pre, "pre_market"), (post, "post_market"), (regular, "regular")):
                    if v and float(v) > 0:
                        price, price_source = float(v), src
                        break

            results.append({
                "symbol": sym,
                "price": price,
                "price_source": price_source,
                "market_state": market_state,
                "regular_market_price": float(regular) if regular else None,
                "pre_market_price": float(pre) if pre else None,
                "post_market_price": float(post) if post else None,
                "regular_market_change_pct": info.get("regularMarketChangePercent"),
                "pre_market_change_pct": info.get("preMarketChangePercent"),
                "post_market_change_pct": info.get("postMarketChangePercent"),
                "currency": info.get("currency", "USD"),
            })
        except Exception as e:
            results.append({"symbol": sym, "error": str(e)})
    return {"quotes": results}


@mcp.tool()
def get_klines(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None,
    limit: int = 250,
) -> dict:
    """Download OHLCV bars. period in {5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd}.
    interval in {1d,1wk,1mo} (yfinance limits intraday to ~60d).
    Returns last `limit` rows.
    """
    start_d, end_d = _resolve_dates(start, end, period)
    df = _svc.load_one(symbol, start_d, end_d, interval=interval, with_indicators=False)
    df = df.tail(limit)
    rows = [
        {
            "date": ts.date().isoformat(),
            "open": float(r.open), "high": float(r.high), "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume) if r.volume == r.volume else None,
        }
        for ts, r in df.iterrows()
    ]
    return {"symbol": symbol.upper(), "interval": interval, "rows": rows}


@mcp.tool()
def get_indicators(
    symbol: str,
    indicators: list[str] | None = None,
    lookback: int = 60,
    period: str = "1y",
) -> dict:
    """Compute technical indicators (ma, rsi, bollinger, kdj) on daily bars.
    Returns the last `lookback` rows with selected indicator columns. If indicators is None, returns all.
    """
    start_d, end_d = _resolve_dates(None, None, period)
    df = _svc.load_one(symbol, start_d, end_d, interval="1d", with_indicators=True)
    df = df.tail(lookback)
    want = set(indicators or [])
    ma_cols = ["ma_5", "ma_10", "ma_20", "ma_50", "ma_100", "ma_200", "ma_250"]
    cols = ["close"]
    if not want or "ma" in want: cols += ma_cols
    if not want or "rsi" in want: cols += ["rsi_14"]
    if not want or "bollinger" in want: cols += ["boll_mid", "boll_upper", "boll_lower"]
    if not want or "kdj" in want: cols += ["kdj_k", "kdj_d", "kdj_j"]
    cols = [c for c in cols if c in df.columns]
    rows = []
    for ts, r in df.iterrows():
        row = {"date": ts.date().isoformat()}
        for c in cols:
            v = r[c]
            row[c] = float(v) if v is not None and v == v else None  # NaN filter
        rows.append(row)
    return {"symbol": symbol.upper(), "indicators": cols, "rows": rows}


if __name__ == "__main__":
    mcp.run()
