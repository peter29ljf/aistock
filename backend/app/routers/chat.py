from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .. import chat_log, event_bus, strategies
from ..claude_runner import run_claude

router = APIRouter(prefix="/api/strategies/{sid}", tags=["chat"])


class ChatBody(BaseModel):
    message: str


@router.get("/chat/history")
def history(sid: str, days: int = 1, limit: int | None = 500):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return chat_log.tail(sid, days=days, limit=limit)


@router.post("/chat")
async def send(sid: str, body: ChatBody):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    msg = body.message.strip()
    if not msg:
        raise HTTPException(400, "empty message")
    entry = chat_log.append(sid, {"role": "user", "content": msg, "kind": "user_message"})
    event_bus.publish(sid, {"type": "user_message", "entry": entry})
    asyncio.create_task(run_claude(sid, "user"))
    return {"ok": True}


@router.get("/chat/stream")
async def stream(sid: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")

    async def gen():
        try:
            async for ev in event_bus.subscribe(sid):
                yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
        except asyncio.CancelledError:
            return

    return EventSourceResponse(gen())
