from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import strategies as strat

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class CreateBody(BaseModel):
    name: str
    description: str = ""


@router.get("")
def list_all():
    return strat.list_strategies()


@router.post("")
def create(body: CreateBody):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    return strat.create_strategy(body.name, body.description)


@router.get("/{sid}")
def get_one(sid: str):
    s = strat.get_strategy(sid)
    if not s:
        raise HTTPException(404, "strategy not found")
    return s


@router.delete("/{sid}")
def delete_one(sid: str):
    if not strat.delete_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return {"ok": True}
