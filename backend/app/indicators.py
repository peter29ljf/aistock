from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


MA_WINDOWS = [5, 10, 20, 50, 100, 200, 250]


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add common technical indicators using only current and prior rows."""
    data = df.sort_index().copy()
    close = data["close"].astype(float)
    high = data["high"].astype(float)
    low = data["low"].astype(float)

    for window in MA_WINDOWS:
        data[f"ma_{window}"] = close.rolling(window=window, min_periods=1).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    data["rsi_14"] = 100 - (100 / (1 + rs))

    mid = close.rolling(window=20, min_periods=1).mean()
    std = close.rolling(window=20, min_periods=1).std(ddof=0)
    data["boll_mid"] = mid
    data["boll_upper"] = mid + 2 * std
    data["boll_lower"] = mid - 2 * std

    lowest_low = low.rolling(window=9, min_periods=1).min()
    highest_high = high.rolling(window=9, min_periods=1).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan) * 100
    data["kdj_k"] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    data["kdj_d"] = data["kdj_k"].ewm(alpha=1 / 3, adjust=False).mean()
    data["kdj_j"] = 3 * data["kdj_k"] - 2 * data["kdj_d"]

    return data.replace({np.nan: None})


def latest_snapshot(df: pd.DataFrame, decision_date: date) -> dict[str, Any] | None:
    visible = df[df.index.date <= decision_date]
    if visible.empty:
        return None
    row = visible.iloc[-1]
    keys = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "rsi_14",
        "boll_mid",
        "boll_upper",
        "boll_lower",
        "kdj_k",
        "kdj_d",
        "kdj_j",
        *[f"ma_{window}" for window in MA_WINDOWS],
    ]
    return {
        key: _clean_value(row.get(key))
        for key in keys
        if key in row.index
    }


def history_window(df: pd.DataFrame, decision_date: date, weeks: int = 52) -> list[dict[str, Any]]:
    end_ts = pd.Timestamp(decision_date)
    start_ts = end_ts - pd.Timedelta(weeks=weeks)
    visible = df[(df.index <= end_ts) & (df.index >= start_ts)]
    records: list[dict[str, Any]] = []
    for timestamp, row in visible.iterrows():
        records.append(
            {
                "date": timestamp.date().isoformat(),
                "open": _clean_value(row["open"]),
                "high": _clean_value(row["high"]),
                "low": _clean_value(row["low"]),
                "close": _clean_value(row["close"]),
                "volume": _clean_value(row.get("volume")),
            }
        )
    return records


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return value
    if isinstance(value, (np.floating, float)):
        return round(float(value), 6)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value
