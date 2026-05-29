from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .. import alerts_db, event_bus, scheduler, strategies as strat
from ..claude_runner import run_claude_cleanup

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


@router.post("/{sid}/cleanup_and_delete")
async def cleanup_and_delete(sid: str):
    """Start cleanup agent then delete. Subscribe to /{sid}/cleanup_stream for progress."""
    if not strat.get_strategy(sid):
        raise HTTPException(404, "strategy not found")

    async def _run():
        channel = f"cleanup:{sid}"
        await run_claude_cleanup(sid)
        # Safety net: cancel any remaining alerts/schedules in DB
        cancelled_alerts = await alerts_db.cancel_all_for_strategy(sid)
        cancelled_jobs = await scheduler.remove_jobs_for_sid(sid)
        if cancelled_alerts or cancelled_jobs:
            event_bus.publish(channel, {
                "type": "cleanup_phase",
                "message": f"数据库清理：{cancelled_alerts} 条告警、{cancelled_jobs} 个定时任务已取消",
            })
        event_bus.publish(channel, {"type": "cleanup_phase", "message": "正在删除策略目录…"})
        strat.delete_strategy(sid)
        event_bus.publish(channel, {"type": "deleted"})

    asyncio.create_task(_run())
    return {"ok": True}


@router.get("/{sid}/cleanup_stream")
async def cleanup_stream(sid: str):
    """SSE stream for cleanup progress. Ends when 'deleted' event is received."""
    channel = f"cleanup:{sid}"

    async def gen():
        try:
            async for ev in event_bus.subscribe(channel):
                yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
                if ev.get("type") == "deleted":
                    return
        except asyncio.CancelledError:
            return

    return EventSourceResponse(gen())
