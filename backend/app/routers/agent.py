from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import strategies as strat

router = APIRouter(prefix="/api/agent", tags=["agent"])


class CreateBody(BaseModel):
    name: str = ""


@router.get("")
def list_sessions():
    return strat.list_strategies(kind="agent")


@router.post("")
def create_session(body: CreateBody):
    return strat.create_agent_session(body.name)


@router.delete("/{sid}")
def delete_session(sid: str):
    s = strat.get_strategy(sid)
    if not s:
        raise HTTPException(404, "session not found")
    if s.get("kind") != "agent":
        raise HTTPException(400, "not an agent session")
    strat.delete_strategy(sid)
    return {"ok": True}
