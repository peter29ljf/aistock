from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


def publish(sid: str, event: dict[str, Any]) -> None:
    for q in list(_subscribers.get(sid, ())):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def subscribe(sid: str) -> AsyncIterator[dict[str, Any]]:
    q: asyncio.Queue = asyncio.Queue(maxsize=1024)
    _subscribers[sid].add(q)
    try:
        while True:
            yield await q.get()
    finally:
        _subscribers[sid].discard(q)
