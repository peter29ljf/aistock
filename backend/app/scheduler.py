"""APScheduler-backed cron + one-shot scheduling.

Jobs persist in SQLite so they survive backend restarts. When a job fires we
append a system event to chat log and spawn a new Claude run with trigger=schedule.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from . import chat_log, event_bus
from .claude_runner import run_claude
from .config import DATA_DIR, SCHEDULES_DB_PATH

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _store() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return {"default": SQLAlchemyJobStore(url=f"sqlite:///{SCHEDULES_DB_PATH}")}


async def start() -> None:
    global _scheduler, _loop
    if _scheduler is not None:
        return
    _loop = asyncio.get_event_loop()
    _scheduler = AsyncIOScheduler(jobstores=_store(), timezone="America/New_York")
    _scheduler.start()
    log.info("scheduler started; %d persisted jobs", len(_scheduler.get_jobs()))


async def stop() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)


def _fire_schedule_entry(sid: str, task_id: str, note: str) -> None:
    """Top-level so APScheduler can serialize a reference to it.
    Runs in APScheduler's thread pool, so use thread-safe event loop submit."""
    chat_log.append(sid, {"role": "system", "kind": "schedule", "task_id": task_id, "note": note})
    event_bus.publish(sid, {"type": "schedule_fired", "task_id": task_id, "note": note})
    if _loop is not None:
        asyncio.run_coroutine_threadsafe(
            run_claude(sid, "schedule", {"task_id": task_id, "note": note}),
            _loop
        )


def _parse_cron(expr: str) -> CronTrigger:
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError("cron must be 5 fields: min hour dom mon dow")
    return CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])


async def add_job(sid: str, *, cron: str | None = None, run_at: str | None = None, note: str = "") -> str:
    assert _scheduler is not None
    task_id = uuid.uuid4().hex[:12]
    if cron:
        trigger = _parse_cron(cron)
        meta = {"kind": "cron", "expr": cron}
    elif run_at:
        trigger = DateTrigger(run_date=datetime.fromisoformat(run_at))
        meta = {"kind": "date", "run_at": run_at}
    else:
        raise ValueError("cron or run_at required")
    _scheduler.add_job(
        _fire_schedule_entry,
        trigger=trigger,
        args=[sid, task_id, note],
        id=task_id,
        name=f"{sid}:{note[:40]}" or sid,
        replace_existing=True,
        misfire_grace_time=300,
    )
    job = _scheduler.get_job(task_id)
    if job:
        job.modify(name=json.dumps({"sid": sid, "note": note, **meta}))
    return task_id


async def list_jobs(sid: str | None = None) -> list[dict[str, Any]]:
    if _scheduler is None:
        return []
    out: list[dict[str, Any]] = []
    for j in _scheduler.get_jobs():
        try:
            meta = json.loads(j.name) if j.name and j.name.startswith("{") else {"sid": None, "note": j.name}
        except json.JSONDecodeError:
            meta = {"sid": None, "note": j.name}
        if sid and meta.get("sid") != sid:
            continue
        out.append({
            "task_id": j.id,
            "sid": meta.get("sid"),
            "note": meta.get("note", ""),
            "kind": meta.get("kind"),
            "expr": meta.get("expr"),
            "run_at": meta.get("run_at"),
            "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
        })
    return out


async def remove_job(task_id: str) -> bool:
    if _scheduler is None:
        return False
    try:
        _scheduler.remove_job(task_id)
        return True
    except Exception:
        return False
