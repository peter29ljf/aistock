from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import scheduler, strategies

router = APIRouter(prefix="/api/strategies/{sid}/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(sid: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return await scheduler.list_jobs(sid)
