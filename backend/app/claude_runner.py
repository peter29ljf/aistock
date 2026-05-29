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


async def run_claude_cleanup(sid: str) -> None:
    """Run a one-shot Claude agent to cancel all orders/alerts/schedules, then publish done."""
    channel = f"cleanup:{sid}"
    cwd = STRATEGIES_DIR / sid
    if not cwd.is_dir():
        event_bus.publish(channel, {"type": "error", "message": "strategy directory not found"})
        event_bus.publish(channel, {"type": "cleanup_done"})
        return

    prompt = (
        f"strategy_id={sid} trigger=cleanup "
        "你的唯一任务是在策略删除前清理所有相关资源，步骤如下：\n"
        "1. 调用 tiger-openapi get_orders 查询所有挂单，对每个状态为 OPEN/PENDING 的订单调用 cancel_order\n"
        "2. 调用 price-alert list_alerts 查询所有 active 告警，逐一调用 cancel_alert\n"
        "3. 调用 scheduler list_tasks 查询所有任务，逐一调用 cancel_task\n"
        "4. 用一段简洁中文汇报取消了哪些内容（没有就说无）\n"
        "不要进行任何分析或新操作，只做清理。"
    )
    args = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "stream-json",
        "--verbose", "--dangerously-skip-permissions",
    ]
    event_bus.publish(channel, {"type": "cleanup_phase", "message": "正在启动清理 agent…"})
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        err = f"claude binary not found at {CLAUDE_BIN}"
        event_bus.publish(channel, {"type": "error", "message": err})
        event_bus.publish(channel, {"type": "cleanup_done"})
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
        event_bus.publish(channel, ev)

    await proc.wait()
    event_bus.publish(channel, {"type": "cleanup_done"})


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
