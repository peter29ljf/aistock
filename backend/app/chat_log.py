from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .config import STRATEGIES_DIR


def _log_path(sid: str, day: date | None = None) -> Path:
    day = day or date.today()
    log_dir = STRATEGIES_DIR / sid / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"chat-{day.isoformat()}.jsonl"


def append(sid: str, entry: dict[str, Any]) -> dict[str, Any]:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    path = _log_path(sid)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def tail(sid: str, days: int = 1, limit: int | None = None) -> list[dict[str, Any]]:
    log_dir = STRATEGIES_DIR / sid / "logs"
    if not log_dir.exists():
        return []
    files = sorted(log_dir.glob("chat-*.jsonl"))[-days:]
    out: list[dict[str, Any]] = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit is not None:
        out = out[-limit:]
    return out
