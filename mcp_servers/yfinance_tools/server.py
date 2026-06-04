#!/usr/bin/env python3
"""MCP: yfinance K-line download + technical indicators + real-time quote."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import time
import urllib.request
import urllib.parse
import json as _json

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from _common import aistock_root

from app.market_data import MarketDataService

mcp = FastMCP("yfinance-tools")

_svc = MarketDataService(aistock_root() / "data" / "kline_cache")

# ── Bitget perpetual contract real-time price ──────────────────────────────────

_BITGET_TICKERS_URL = "https://api.bitget.com/api/v2/mix/market/tickers"
_BITGET_TICKER_URL  = "https://api.bitget.com/api/v2/mix/market/ticker"
# Bulk cache: populated by one call that fetches ALL 590+ contracts at once
_BITGET_BULK_CACHE: dict[str, dict] = {}   # bg_symbol -> parsed dict
_BITGET_BULK_TS: float = 0.0
_BITGET_BULK_TTL = 4.0   # seconds — refresh all tickers every 4s


def _parse_bitget_item(d: dict) -> dict:
    return {
        "price":         float(d["lastPr"]),
        "bid":           float(d["bidPr"]),
        "ask":           float(d["askPr"]),
        "mark_price":    float(d["markPrice"]),
        "index_price":   float(d["indexPrice"]) if d.get("indexPrice") else None,
        "change_24h_pct": float(d["change24h"]) * 100,
        "high_24h":      float(d["high24h"]),
        "low_24h":       float(d["low24h"]),
        "funding_rate":  float(d["fundingRate"]) if d.get("fundingRate") else None,
        "source":        "bitget_perp",
        "ts_ms":         int(d["ts"]),
    }


def _refresh_bulk_cache() -> bool:
    """Fetch ALL USDT perpetual tickers in one request and populate the cache."""
    global _BITGET_BULK_TS
    try:
        url = _BITGET_TICKERS_URL + "?productType=usdt-futures"
        req = urllib.request.Request(url, headers={"User-Agent": "aistock/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = _json.loads(resp.read())
        if raw.get("code") != "00000":
            return False
        for d in raw.get("data") or []:
            _BITGET_BULK_CACHE[d["symbol"]] = _parse_bitget_item(d)
        _BITGET_BULK_TS = time.time()
        return True
    except Exception:
        return False


def _bitget_quote(symbol: str) -> dict | None:
    """Real-time price from Bitget USDT perpetual (e.g. NVDA → NVDAUSDT).
    Uses bulk cache (all tickers fetched in one request, TTL 4s).
    Falls back to single-symbol request if bulk fetch fails.
    """
    global _BITGET_BULK_TS
    bg_sym = symbol.upper() + "USDT"
    now = time.time()

    # Refresh bulk cache if stale
    if now - _BITGET_BULK_TS > _BITGET_BULK_TTL:
        _refresh_bulk_cache()

    if bg_sym in _BITGET_BULK_CACHE:
        return _BITGET_BULK_CACHE[bg_sym]

    # Single-symbol fallback (e.g. bulk fetch failed)
    try:
        url = _BITGET_TICKER_URL + "?" + urllib.parse.urlencode({
            "symbol": bg_sym, "productType": "usdt-futures"
        })
        req = urllib.request.Request(url, headers={"User-Agent": "aistock/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw = _json.loads(resp.read())
        items = raw.get("data") or []
        if not items:
            return None
        result = _parse_bitget_item(items[0])
        _BITGET_BULK_CACHE[bg_sym] = result
        return result
    except Exception:
        return None


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
    """Get real-time stock price. Primary: Bitget USDT perpetual (~100ms lag, 24h).
    Fallback: yfinance (~15min delay). Works pre/post market without broker subscription.

    Returned fields:
      price         – latest trade price
      source        – 'bitget_perp' | 'yfinance_pre' | 'yfinance_regular' | 'yfinance_post'
      bid/ask       – best bid/ask (Bitget only)
      mark_price    – mark price (Bitget only)
      change_24h_pct – 24h change % (Bitget) or session change % (yfinance)
    """
    results = []
    for sym in symbols:
        sym = sym.upper()
        # ── Primary: Bitget perpetual ──────────────────────────────────────────
        bg = _bitget_quote(sym)
        if bg:
            results.append({
                "symbol": sym,
                "price": bg["price"],
                "source": "bitget_perp",
                "bid": bg["bid"],
                "ask": bg["ask"],
                "mark_price": bg["mark_price"],
                "index_price": bg["index_price"],
                "change_24h_pct": bg["change_24h_pct"],
                "high_24h": bg["high_24h"],
                "low_24h": bg["low_24h"],
                "funding_rate": bg["funding_rate"],
                "ts_ms": bg["ts_ms"],
            })
            continue

        # ── Fallback: yfinance (15-min delay) ─────────────────────────────────
        try:
            info = yf.Ticker(sym).info
            market_state = info.get("marketState", "UNKNOWN")
            pre = info.get("preMarketPrice")
            post = info.get("postMarketPrice")
            regular = info.get("regularMarketPrice")

            if market_state in ("PRE", "PREPRE") and pre and float(pre) > 0:
                price, src = float(pre), "yfinance_pre"
            elif market_state in ("POST", "POSTPOST") and post and float(post) > 0:
                price, src = float(post), "yfinance_post"
            elif regular and float(regular) > 0:
                price, src = float(regular), "yfinance_regular"
            else:
                price, src = None, None
                for v, s in ((pre, "yfinance_pre"), (post, "yfinance_post"), (regular, "yfinance_regular")):
                    if v and float(v) > 0:
                        price, src = float(v), s
                        break

            results.append({
                "symbol": sym,
                "price": price,
                "source": src,
                "market_state": market_state,
                "regular_market_price": float(regular) if regular else None,
                "pre_market_price": float(pre) if pre else None,
                "post_market_price": float(post) if post else None,
                "change_24h_pct": info.get("regularMarketChangePercent"),
                "currency": info.get("currency", "USD"),
                "warning": "yfinance fallback (~15min delay) — symbol not on Bitget perp",
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
