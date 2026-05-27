from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import portfolio_io, quote_cache, strategies

router = APIRouter(prefix="/api/strategies/{sid}/portfolio", tags=["portfolio"])


class AddBody(BaseModel):
    symbol: str
    buy_price: float
    quantity: float
    note: str = ""


class UpdateBody(BaseModel):
    buy_price: float | None = None
    quantity: float | None = None
    note: str | None = None


def _decorate(sid: str):
    data = portfolio_io.load(sid)
    out = []
    for p in data.get("positions", []):
        cur = quote_cache.get(p["symbol"])
        item = dict(p)
        if cur is not None:
            item["current_price"] = round(cur, 4)
            try:
                item["pnl_value"] = round((cur - p["buy_price"]) * p["quantity"], 4)
                if p["buy_price"]:
                    item["pnl_pct"] = round((cur / p["buy_price"] - 1) * 100, 3)
            except (TypeError, ZeroDivisionError):
                pass
        out.append(item)
    return out


@router.get("")
def list_positions(sid: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return _decorate(sid)


@router.post("")
def add_position(sid: str, body: AddBody):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    portfolio_io.add(sid, body.symbol, body.buy_price, body.quantity, body.note)
    return _decorate(sid)


@router.patch("/{symbol}")
def update_position(sid: str, symbol: str, body: UpdateBody):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    if portfolio_io.update(sid, symbol, **body.model_dump(exclude_none=True)) is None:
        raise HTTPException(404, "position not found")
    return _decorate(sid)


@router.delete("/{symbol}")
def remove_position(sid: str, symbol: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    if not portfolio_io.remove(sid, symbol):
        raise HTTPException(404, "position not found")
    return _decorate(sid)
