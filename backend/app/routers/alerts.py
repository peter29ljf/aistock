from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import alerts_db, strategies

router = APIRouter(prefix="/api/strategies/{sid}/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(sid: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return await alerts_db.list_for_strategy(sid)
