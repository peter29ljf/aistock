from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from ..config import MCP_SERVERS_DIR, ROOT, TIGER_PYTHON
from .. import scheduler as _scheduler_mod

router = APIRouter(prefix="/api/health", tags=["health"])

# ── Cache so rapid refreshes don't re-run subprocess checks ──────────────────
_cache: dict[str, Any] = {}
_CACHE_TTL = 30  # seconds


def _cached(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _store(key: str, data: dict) -> dict:
    _cache[key] = {"ts": time.time(), "data": data}
    return data


# ── Individual checks ─────────────────────────────────────────────────────────

async def _check_python_import(package: str, python: str = "python3", timeout: float = 5.0) -> tuple[bool, str]:
    """Return (ok, detail) by running a subprocess import test."""
    try:
        proc = await asyncio.create_subprocess_exec(
            python, "-c", f"import {package}; print('ok')",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return False, "超时"
        if proc.returncode == 0:
            return True, ""
        # Extract the last line of the error (most informative)
        lines = err.decode("utf-8", errors="replace").strip().splitlines()
        return False, lines[-1][:100] if lines else "未知错误"
    except Exception as e:
        return False, str(e)[:100]


async def _check_tiger() -> dict:
    cached = _cached("tiger")
    if cached:
        return cached

    server_py = Path("/Users/junfenglin/workspace/tigerskill/tiger-mcp-server/server.py")
    props = Path("/Users/junfenglin/workspace/tigerskill/tiger_openapi_config.properties")

    if not server_py.exists():
        return _store("tiger", {"status": "error", "detail": "server.py 未找到"})
    if not props.exists():
        return _store("tiger", {"status": "error", "detail": ".properties 凭证文件未找到"})

    # tiger MCP uses the framework Python (not the backend venv which lacks tigeropen)
    ok, detail = await _check_python_import("tigeropen", python=TIGER_PYTHON)
    if not ok:
        return _store("tiger", {"status": "error", "detail": f"tigeropen 未安装: {detail}"})

    return _store("tiger", {"status": "ok", "detail": "配置文件已就绪"})


async def _check_yfinance() -> dict:
    cached = _cached("yfinance")
    if cached:
        return cached

    server_py = MCP_SERVERS_DIR / "yfinance_tools" / "server.py"
    if not server_py.exists():
        return _store("yfinance", {"status": "error", "detail": "server.py 未找到"})

    ok, detail = await _check_python_import("yfinance")
    if not ok:
        return _store("yfinance", {"status": "error", "detail": f"yfinance 未安装: {detail}"})
    return _store("yfinance", {"status": "ok", "detail": ""})


def _check_local(name: str, rel_path: str) -> dict:
    cached = _cached(name)
    if cached:
        return cached
    p = MCP_SERVERS_DIR / rel_path
    if p.exists():
        return _store(name, {"status": "ok", "detail": ""})
    return _store(name, {"status": "error", "detail": f"{rel_path} 未找到"})


async def _check_scheduler() -> dict:
    cached = _cached("scheduler")
    if cached:
        return cached
    jobs = await _scheduler_mod.list_jobs()
    return _store("scheduler", {"status": "ok", "detail": f"{len(jobs)} 个定时任务", "jobs": len(jobs)})


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/mcp")
async def mcp_health():
    tiger, yfinance, sched = await asyncio.gather(
        _check_tiger(),
        _check_yfinance(),
        _check_scheduler(),
    )
    return {
        "tiger-openapi":  tiger,
        "yfinance-tools": yfinance,
        "portfolio":      _check_local("portfolio",    "portfolio/server.py"),
        "strategy-doc":   _check_local("strategy-doc", "strategy_doc/server.py"),
        "price-alert":    _check_local("price-alert",  "price_alert/server.py"),
        "scheduler":      sched,
    }
