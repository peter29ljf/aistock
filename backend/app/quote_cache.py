"""Lightweight current-price cache used to compute portfolio P&L.

Uses yfinance fast_info for a simple non-real-time fallback. The IB watcher (Phase 3)
will replace this with its in-memory ticker map when running.
"""

from __future__ import annotations

import time
from typing import Optional

import yfinance as yf

_TTL_SEC = 10.0
_cache: dict[str, tuple[float, float]] = {}

_ib_provider = None  # set by ib_watcher at startup; callable(symbol)->price|None


def set_ib_provider(fn) -> None:
    global _ib_provider
    _ib_provider = fn


def get(symbol: str) -> Optional[float]:
    symbol = symbol.upper()
    if _ib_provider:
        try:
            p = _ib_provider(symbol)
            if p is not None:
                return float(p)
        except Exception:
            pass
    now = time.time()
    if symbol in _cache:
        ts, val = _cache[symbol]
        if now - ts < _TTL_SEC:
            return val
    try:
        t = yf.Ticker(symbol)
        full = t.info
        # 盘前/盘后 > 正规市场价，确保持仓显示盘前盘后最新价
        for key in ("preMarketPrice", "postMarketPrice", "regularMarketPrice"):
            v = full.get(key)
            if v and float(v) > 0:
                _cache[symbol] = (now, float(v))
                return float(v)
        fast = t.fast_info
        price = float(fast.get("lastPrice") or fast.get("last_price") or 0) or None
        if price:
            _cache[symbol] = (now, price)
        return price
    except Exception:
        return None
