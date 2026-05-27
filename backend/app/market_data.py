"""Lightweight yfinance loader for aistock. Adapted from llmtrade/backend/app/market_data.py.

Removed the SymbolSearchResult dependency so this module is self-contained.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf

from .indicators import add_indicators


class MarketDataError(RuntimeError):
    pass


class MarketDataService:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_one(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: str = "1d",
        with_indicators: bool = True,
    ) -> pd.DataFrame:
        cache_path = self.cache_dir / (
            f"{_safe(symbol)}_{interval}_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        )
        if cache_path.exists():
            frame = pd.read_csv(cache_path, parse_dates=["date"])
        else:
            raw = yf.download(
                symbol,
                start=start_date.isoformat(),
                end=(end_date + timedelta(days=1)).isoformat(),
                interval=interval,
                auto_adjust=False,
                progress=False,
                group_by="column",
                threads=False,
            )
            if raw.empty:
                raise MarketDataError(f"No data for {symbol}")
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            frame = raw.reset_index().rename(
                columns={
                    "Date": "date",
                    "Datetime": "date",
                    "index": "date",   # yfinance 1.2.0: index.name=None → reset_index() → "index"
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adj_close",
                    "Volume": "volume",
                }
            )
            required = ["date", "open", "high", "low", "close", "volume"]
            missing = [c for c in required if c not in frame.columns]
            if missing:
                raise MarketDataError(f"{symbol} missing columns: {missing}")
            frame = frame[required].dropna(subset=["open", "high", "low", "close"])
            frame.to_csv(cache_path, index=False)

        normalized = _normalize(frame)
        if with_indicators and len(normalized) >= 5:
            try:
                normalized = add_indicators(normalized)
            except Exception:
                pass
        return normalized

    def load_many(
        self, symbols: Iterable[str], start_date: date, end_date: date, interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        return {s: self.load_one(s, start_date, end_date, interval) for s in symbols}


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    out = out.set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["open", "high", "low", "close"])


def _safe(symbol: str) -> str:
    return symbol.replace("^", "INDEX_").replace("/", "_").replace(".", "_").upper()
