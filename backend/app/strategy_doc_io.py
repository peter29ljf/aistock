from __future__ import annotations

from pathlib import Path

from .config import STRATEGIES_DIR


def _path(sid: str) -> Path:
    return STRATEGIES_DIR / sid / "strategy.md"


def read(sid: str) -> str:
    p = _path(sid)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def write(sid: str, markdown: str) -> None:
    p = _path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")


def append(sid: str, text: str) -> None:
    existing = read(sid)
    sep = "" if existing.endswith("\n") else "\n"
    write(sid, existing + sep + text + "\n")
