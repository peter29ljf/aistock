from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGIES_DIR = ROOT / "strategies"
DATA_DIR = ROOT / "data"
KLINE_CACHE_DIR = DATA_DIR / "kline_cache"
MCP_SERVERS_DIR = ROOT / "mcp_servers"

ALERTS_DB_PATH = DATA_DIR / "alerts.sqlite"
SCHEDULES_DB_PATH = DATA_DIR / "schedules.sqlite"

CLAUDE_BIN = os.environ.get("AISTOCK_CLAUDE_BIN", "/Users/junfenglin/.local/bin/claude")
VENV_PYTHON = os.environ.get("AISTOCK_VENV_PYTHON", str(ROOT / "backend" / ".venv" / "bin" / "python"))
# Python used by the tiger-openapi MCP server (must have tigeropen installed)
TIGER_PYTHON = os.environ.get("AISTOCK_TIGER_PYTHON", "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3")

IB_HOST = os.environ.get("AISTOCK_IB_HOST", "127.0.0.1")
IB_PORT = int(os.environ.get("AISTOCK_IB_PORT", "4001"))
IB_CLIENT_ID = int(os.environ.get("AISTOCK_IB_CLIENT_ID", "11"))

API_HOST = os.environ.get("AISTOCK_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("AISTOCK_API_PORT", "8000"))
API_BASE = f"http://{API_HOST}:{API_PORT}"

_TOKEN_FILE = DATA_DIR / "internal_token"


def internal_token() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _TOKEN_FILE.exists():
        return _TOKEN_FILE.read_text().strip()
    token = secrets.token_urlsafe(32)
    _TOKEN_FILE.write_text(token)
    return token


def ensure_dirs() -> None:
    for p in (STRATEGIES_DIR, DATA_DIR, KLINE_CACHE_DIR):
        p.mkdir(parents=True, exist_ok=True)
