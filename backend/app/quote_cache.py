"""Lightweight current-price cache used to compute portfolio P&L.

Priority:
  1. IB watcher live tick (when IB Gateway is connected)
  2. Bitget USDT perpetual (~100ms lag, 5s bulk cache)
  3. yfinance session-aware fallback (~15min delay, last resort)
"""

from __future__ import annotations

import time
from typing import Optional

import yfinance as yf

_TTL_SEC = 10.0
_yf_cache: dict[str, tuple[float, float]] = {}   # symbol -> (ts, price)

_ib_provider = None  # set by ib_watcher at startup; callable(symbol)->price|None


def set_ib_provider(fn) -> None:
    global _ib_provider
    _ib_provider = fn


def _yf_session_price(symbol: str) -> Optional[float]:
    """Fetch price from yfinance, picking the right field for the current session."""
    from .bitget_quote import us_session
    now = time.time()
    cached = _yf_cache.get(symbol)
    if cached and now - cached[0] < _TTL_SEC:
        return cached[1]
    try:
        info = yf.Ticker(symbol).info
        session = us_session()
        pre     = info.get("preMarketPrice")
        post    = info.get("postMarketPrice")
        regular = info.get("regularMarketPrice")
        def _f(v): return float(v) if v and float(v) > 0 else None

        if session == "pre"       and _f(pre):     price = _f(pre)
        elif session == "regular" and _f(regular): price = _f(regular)
        elif session == "post"    and _f(post):    price = _f(post)
        else:                                      # closed
            price = _f(post) or _f(regular) or _f(pre)

        if price:
            _yf_cache[symbol] = (now, price)
        return price
    except Exception:
        return None


def get(symbol: str) -> Optional[float]:
    """Return best available current price for portfolio P&L."""
    symbol = symbol.upper()

    # 1. IB live tick
    if _ib_provider:
        try:
            p = _ib_provider(symbol)
            if p is not None:
                return float(p)
        except Exception:
            pass

    # 2. Bitget perpetual (real-time, 5s bulk cache)
    try:
        from .bitget_quote import get as bitget_get
        p = bitget_get(symbol)
        if p is not None:
            return float(p)
    except Exception:
        pass

    # 3. yfinance session-aware fallback
    return _yf_session_price(symbol)
