from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@asynccontextmanager
async def strategy_lock(sid: str):
    lock = _locks[sid]
    await lock.acquire()
    try:
        yield
    finally:
        lock.release()
