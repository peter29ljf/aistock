"""Localhost-only endpoints used by MCP servers to notify the backend or
to schedule/alert work the backend owns.

Token auth via header `X-Aistock-Token`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .. import chat_log, event_bus, strategies
from ..config import internal_token

router = APIRouter(prefix="/_internal", tags=["internal"])


def _auth(token: str | None) -> None:
    if token != internal_token():
        raise HTTPException(401, "bad token")


class NotifyBody(BaseModel):
    sid: str
    kind: str  # "portfolio_changed" | "strategy_doc_changed"
    payload: dict[str, Any] | None = None


@router.post("/notify")
def notify(body: NotifyBody, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    event_bus.publish(body.sid, {"type": body.kind, "payload": body.payload or {}})
    return {"ok": True}


class AlertCreateBody(BaseModel):
    sid: str
    symbol: str
    target_price: float
    direction: str  # "above" | "below"
    note: str = ""


@router.post("/alerts")
async def create_alert(body: AlertCreateBody, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    if not strategies.get_strategy(body.sid):
        raise HTTPException(404, "strategy not found")
    if body.direction not in ("above", "below"):
        raise HTTPException(400, "direction must be above|below")
    from .. import alerts_db, ib_watcher
    aid = await alerts_db.create(body.sid, body.symbol.upper(), float(body.target_price), body.direction, body.note)
    await ib_watcher.reconcile()
    return {"alert_id": aid}


@router.get("/alerts")
async def list_alerts(sid: str | None = None, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    from .. import alerts_db
    return await alerts_db.list_active(sid)


@router.delete("/alerts/{alert_id}")
async def cancel_alert(alert_id: int, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    from .. import alerts_db, ib_watcher
    ok = await alerts_db.cancel(alert_id)
    await ib_watcher.reconcile()
    return {"ok": ok}


class ScheduleCreateBody(BaseModel):
    sid: str
    cron: str | None = None        # 5-field cron
    run_at: str | None = None      # ISO8601 for one-shot
    note: str = ""


@router.post("/schedules")
async def create_schedule(body: ScheduleCreateBody, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    if not strategies.get_strategy(body.sid):
        raise HTTPException(404, "strategy not found")
    if not body.cron and not body.run_at:
        raise HTTPException(400, "cron or run_at required")
    from ..scheduler import add_job
    tid = await add_job(body.sid, cron=body.cron, run_at=body.run_at, note=body.note)
    return {"task_id": tid}


@router.get("/schedules")
async def list_schedules(sid: str | None = None, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    from ..scheduler import list_jobs
    return await list_jobs(sid)


@router.delete("/schedules/{task_id}")
async def cancel_schedule(task_id: str, x_aistock_token: str | None = Header(default=None)):
    _auth(x_aistock_token)
    from ..scheduler import remove_job
    ok = await remove_job(task_id)
    return {"ok": ok}
