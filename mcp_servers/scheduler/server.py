#!/usr/bin/env python3
"""MCP: cron + one-shot scheduling via backend APScheduler."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP
from _common import api_delete, api_get, api_post, strategy_id

mcp = FastMCP("scheduler")


@mcp.tool()
def schedule_task(cron: str, note: str = "") -> dict:
    """Schedule a recurring task. cron is a 5-field expression: 'min hour dom mon dow'.
    Example: '30 9 * * 1-5' (every weekday 09:30 ET).
    On fire, a new Claude run starts with trigger=schedule.
    Returns {"task_id": str}.
    """
    sid = strategy_id()
    return api_post("/_internal/schedules", {"sid": sid, "cron": cron, "note": note})


@mcp.tool()
def schedule_once(run_at: str, note: str = "") -> dict:
    """Schedule a single one-shot task. run_at is ISO8601 (e.g. '2026-05-27T09:31:00').
    Returns {"task_id": str}.
    """
    sid = strategy_id()
    return api_post("/_internal/schedules", {"sid": sid, "run_at": run_at, "note": note})


@mcp.tool()
def list_tasks() -> dict:
    """List scheduled tasks for this strategy."""
    rows = api_get("/_internal/schedules", {"sid": strategy_id()})
    return {"tasks": rows}


@mcp.tool()
def cancel_task(task_id: str) -> dict:
    """Cancel a scheduled task by id."""
    return api_delete(f"/_internal/schedules/{task_id}")


if __name__ == "__main__":
    mcp.run()
