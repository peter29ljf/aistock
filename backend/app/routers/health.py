from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from ..config import MCP_SERVERS_DIR, TIGER_PYTHON
from .. import scheduler as _scheduler_mod

router = APIRouter(prefix="/api/health", tags=["health"])

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict[str, Any] = {}
_CACHE_TTL = 30  # seconds for fast checks
_LIVE_CACHE_TTL = 60  # seconds for live tiger check


def _cached(key: str, ttl: float = _CACHE_TTL) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < ttl:
        return entry["data"]
    return None


def _store(key: str, data: dict) -> dict:
    _cache[key] = {"ts": time.time(), "data": data}
    return data


# ── Tiger: fast config check (no network) ─────────────────────────────────────

_TIGER_SERVER = Path("/Users/junfenglin/workspace/tigerskill/tiger-mcp-server/server.py")
_TIGER_PROPS  = Path("/Users/junfenglin/workspace/tigerskill/tiger_openapi_config.properties")

# Tiger: live connectivity check (calls get_market_status)
_TIGER_LIVE_PROBE = """
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Language
cfg = TigerOpenClientConfig(props_path={props!r})
cfg.language = Language.en_US
client = QuoteClient(cfg)
status = client.get_market_status(["US"])
print("ok")
"""


async def _run_probe(script: str, timeout: float) -> tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            TIGER_PYTHON, "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0 and b"ok" in out:
            return True, ""
        lines = err.decode("utf-8", errors="replace").strip().splitlines()
        return False, (lines[-1] if lines else "失败")[:120]
    except asyncio.TimeoutError:
        try: proc.kill()
        except Exception: pass
        return False, f"超时 (>{int(timeout)}s)"
    except Exception as e:
        return False, str(e)[:120]


def _check_tiger_config() -> dict:
    """Pure file check — no subprocess, no network."""
    cached = _cached("tiger_config")
    if cached:
        return cached
    if not _TIGER_SERVER.exists():
        return _store("tiger_config", {"status": "error", "detail": "server.py 未找到", "mode": "config"})
    if not _TIGER_PROPS.exists():
        return _store("tiger_config", {"status": "error", "detail": ".properties 未找到", "mode": "config"})
    # Parse properties file directly — no tigeropen import needed
    try:
        text = _TIGER_PROPS.read_text(encoding="utf-8", errors="replace")
        keys = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        # Accept either private_key_pk8 (RSA PKCS8) or private_key_pk1 (PKCS1)
        has_key = bool(keys & {"private_key_pk8", "private_key_pk1", "private_key"})
        missing = set()
        if "tiger_id" not in keys:
            missing.add("tiger_id")
        if not has_key:
            missing.add("private_key")
        if missing:
            return _store("tiger_config", {"status": "error", "detail": f"凭证缺少字段: {', '.join(missing)}", "mode": "config"})
        return _store("tiger_config", {"status": "ok", "detail": "凭证已配置", "mode": "config"})
    except Exception as e:
        return _store("tiger_config", {"status": "error", "detail": str(e)[:80], "mode": "config"})


async def _check_tiger_live() -> dict:
    cached = _cached("tiger_live", ttl=_LIVE_CACHE_TTL)
    if cached:
        return cached
    if not _TIGER_PROPS.exists():
        return _store("tiger_live", {"status": "error", "detail": ".properties 未找到", "mode": "live"})
    script = _TIGER_LIVE_PROBE.format(props=str(_TIGER_PROPS))
    ok, detail = await _run_probe(script, timeout=12.0)
    if ok:
        return _store("tiger_live", {"status": "ok", "detail": "API 可达", "mode": "live"})
    return _store("tiger_live", {"status": "error", "detail": detail, "mode": "live"})


# ── yfinance: import check ────────────────────────────────────────────────────

async def _check_yfinance() -> dict:
    cached = _cached("yfinance")
    if cached:
        return cached
    if not (MCP_SERVERS_DIR / "yfinance_tools" / "server.py").exists():
        return _store("yfinance", {"status": "error", "detail": "server.py 未找到"})
    ok, detail = await _run_probe("import yfinance; print('ok')", timeout=5.0)
    if ok:
        return _store("yfinance", {"status": "ok", "detail": ""})
    return _store("yfinance", {"status": "error", "detail": detail})


# ── Local MCP servers: file-exists check ─────────────────────────────────────

def _check_local(name: str, rel_path: str) -> dict:
    cached = _cached(name)
    if cached:
        return cached
    p = MCP_SERVERS_DIR / rel_path
    if p.exists():
        return _store(name, {"status": "ok", "detail": ""})
    return _store(name, {"status": "error", "detail": f"{rel_path} 未找到"})


# ── Scheduler ─────────────────────────────────────────────────────────────────

async def _check_scheduler() -> dict:
    cached = _cached("scheduler")
    if cached:
        return cached
    jobs = await _scheduler_mod.list_jobs()
    return _store("scheduler", {"status": "ok", "detail": f"{len(jobs)} 个定时任务", "jobs": len(jobs)})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/mcp")
async def mcp_health():
    """Fast health check (< 5s). Tiger shows config status only."""
    yfinance, sched = await asyncio.gather(
        _check_yfinance(),
        _check_scheduler(),
    )
    return {
        "tiger-openapi":  _check_tiger_config(),
        "yfinance-tools": yfinance,
        "portfolio":      _check_local("portfolio",    "portfolio/server.py"),
        "strategy-doc":   _check_local("strategy-doc", "strategy_doc/server.py"),
        "price-alert":    _check_local("price-alert",  "price_alert/server.py"),
        "scheduler":      sched,
    }


@router.get("/mcp/tiger_live")
async def tiger_live_check():
    """Slow live check — actually calls Tiger get_market_status (up to 12s)."""
    return await _check_tiger_live()
