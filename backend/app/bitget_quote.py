"""Bitget USDT perpetual real-time price cache.

One bulk request fetches all 590+ contracts at once and caches them.
Subsequent lookups (per symbol) are served from in-process memory in <1ms.
Cache TTL is 5 seconds — stale data triggers a background refresh.

Usage:
    from app.bitget_quote import get as bitget_get
    price = bitget_get("NVDA")   # returns float or None if not on Bitget
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

_TICKERS_URL = "https://api.bitget.com/api/v2/mix/market/tickers?productType=usdt-futures"
_CACHE_TTL   = 5.0   # seconds between full refreshes

_bulk_cache: dict[str, float] = {}   # "NVDAUSDT" -> last price
_bulk_ts: float = 0.0

# ── Session helper (shared with yfinance MCP logic) ───────────────────────────

_ET = ZoneInfo("America/New_York")
_SESSION_WINDOWS = [
    (dtime(4,  0), dtime(9, 30), "pre"),
    (dtime(9, 30), dtime(16, 0), "regular"),
    (dtime(16, 0), dtime(20, 0), "post"),
]


def us_session() -> str:
    """Return current US market session string (DST-aware)."""
    now_et = datetime.now(_ET)
    if now_et.weekday() >= 5:
        return "closed"
    t = now_et.time().replace(tzinfo=None)
    for start, end, name in _SESSION_WINDOWS:
        if start <= t < end:
            return name
    return "closed"


# ── Bulk cache management ─────────────────────────────────────────────────────

def _refresh() -> bool:
    global _bulk_ts
    try:
        req = urllib.request.Request(_TICKERS_URL, headers={"User-Agent": "aistock/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = json.loads(resp.read())
        if raw.get("code") != "00000":
            return False
        for d in raw.get("data") or []:
            sym = d.get("symbol", "")
            try:
                _bulk_cache[sym] = float(d["lastPr"])
            except (KeyError, ValueError):
                pass
        _bulk_ts = time.time()
        log.debug("Bitget bulk cache refreshed: %d contracts", len(_bulk_cache))
        return True
    except Exception as e:
        log.warning("Bitget bulk refresh failed: %s", e)
        return False


def get(symbol: str) -> float | None:
    """Return real-time last price from Bitget perpetual, or None if unavailable.

    Automatically refreshes the bulk cache when TTL expires.
    """
    global _bulk_ts
    if time.time() - _bulk_ts > _CACHE_TTL:
        _refresh()
    key = symbol.upper() + "USDT"
    return _bulk_cache.get(key)


def get_many(symbols: list[str]) -> dict[str, float | None]:
    """Return {symbol: price_or_None} for multiple symbols in one cache hit."""
    global _bulk_ts
    if time.time() - _bulk_ts > _CACHE_TTL:
        _refresh()
    return {sym: _bulk_cache.get(sym.upper() + "USDT") for sym in symbols}
