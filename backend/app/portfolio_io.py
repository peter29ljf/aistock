from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import STRATEGIES_DIR


def _path(sid: str) -> Path:
    return STRATEGIES_DIR / sid / "portfolio.json"


def load(sid: str) -> dict[str, Any]:
    p = _path(sid)
    if not p.exists():
        return {"positions": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"positions": []}


def save(sid: str, data: dict[str, Any]) -> None:
    p = _path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add(sid: str, symbol: str, buy_price: float, quantity: float, note: str = "") -> dict[str, Any]:
    d = load(sid)
    positions = d.setdefault("positions", [])
    symbol = symbol.upper()
    for p in positions:
        if p.get("symbol") == symbol:
            p["buy_price"] = float(buy_price)
            p["quantity"] = float(quantity)
            if note:
                p["note"] = note
            save(sid, d)
            return p
    pos = {"symbol": symbol, "buy_price": float(buy_price), "quantity": float(quantity), "note": note}
    positions.append(pos)
    save(sid, d)
    return pos


def update(sid: str, symbol: str, **fields) -> dict[str, Any] | None:
    d = load(sid)
    symbol = symbol.upper()
    for p in d.get("positions", []):
        if p.get("symbol") == symbol:
            for k, v in fields.items():
                if v is None:
                    continue
                if k in ("buy_price", "quantity"):
                    p[k] = float(v)
                else:
                    p[k] = v
            save(sid, d)
            return p
    return None


def remove(sid: str, symbol: str) -> bool:
    d = load(sid)
    symbol = symbol.upper()
    before = len(d.get("positions", []))
    d["positions"] = [p for p in d.get("positions", []) if p.get("symbol") != symbol]
    if len(d["positions"]) != before:
        save(sid, d)
        return True
    return False
