from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from . import chat_log, event_bus
from .config import CLAUDE_BIN, STRATEGIES_DIR
from .strategy_lock import strategy_lock

log = logging.getLogger(__name__)


def _build_prompt(sid: str, trigger: str, extras: dict[str, Any] | None) -> str:
    parts = [f"strategy_id={sid}", f"trigger={trigger}"]
    for k, v in (extras or {}).items():
        s = str(v).replace(" ", "_")
        parts.append(f"{k}={s}")
    return " ".join(parts)


async def run_claude(sid: str, trigger: str, extras: dict[str, Any] | None = None) -> None:
    cwd = STRATEGIES_DIR / sid
    if not cwd.is_dir():
        log.warning("run_claude: strategy %s not found", sid)
        return

    async with strategy_lock(sid):
        prompt = _build_prompt(sid, trigger, extras)
        args = [
            CLAUDE_BIN,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
        ]
        event_bus.publish(sid, {"type": "run_started", "trigger": trigger, "prompt": prompt})
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            err = f"claude binary not found at {CLAUDE_BIN}"
            event_bus.publish(sid, {"type": "error", "message": err})
            chat_log.append(sid, {"role": "system", "kind": "error", "message": err})
            return

        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                ev = {"type": "raw", "data": line}
            event_bus.publish(sid, ev)
            chat_log.append(sid, ev)

        rc = await proc.wait()
        stderr = b""
        if proc.stderr is not None:
            stderr = await proc.stderr.read()
        if rc != 0:
            msg = f"claude exited code={rc} stderr={stderr.decode('utf-8','replace')[:500]}"
            event_bus.publish(sid, {"type": "error", "message": msg})
            chat_log.append(sid, {"role": "system", "kind": "error", "message": msg})
        event_bus.publish(sid, {"type": "done", "trigger": trigger, "returncode": rc})
