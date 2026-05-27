"""Shared helpers for aistock MCP servers."""

from __future__ import annotations

import os
from pathlib import Path

import httpx


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None:
        raise RuntimeError(f"env {name} not set")
    return v


def strategy_id() -> str:
    return env("STRATEGY_ID")


def aistock_root() -> Path:
    return Path(env("AISTOCK_ROOT", str(Path(__file__).resolve().parents[1])))


def api_base() -> str:
    return env("AISTOCK_API", "http://127.0.0.1:8000")


def internal_token() -> str:
    return env("AISTOCK_TOKEN", "")


def notify(sid: str, kind: str, payload: dict | None = None) -> None:
    try:
        httpx.post(
            f"{api_base()}/_internal/notify",
            json={"sid": sid, "kind": kind, "payload": payload or {}},
            headers={"X-Aistock-Token": internal_token()},
            timeout=3.0,
        )
    except Exception:
        pass


def api_post(path: str, body: dict) -> dict:
    r = httpx.post(
        f"{api_base()}{path}",
        json=body,
        headers={"X-Aistock-Token": internal_token()},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()


def api_get(path: str, params: dict | None = None) -> dict | list:
    r = httpx.get(
        f"{api_base()}{path}",
        params=params or {},
        headers={"X-Aistock-Token": internal_token()},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()


def api_delete(path: str) -> dict:
    r = httpx.delete(
        f"{api_base()}{path}",
        headers={"X-Aistock-Token": internal_token()},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json()
