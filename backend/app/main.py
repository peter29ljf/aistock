from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import ib_watcher, scheduler
from .config import ensure_dirs
from .routers import agent as agent_router
from .routers import alerts as alerts_router
from .routers import chat as chat_router
from .routers import health as health_router
from .routers import internal as internal_router
from .routers import portfolio as portfolio_router
from .routers import schedules as schedules_router
from .routers import strategies as strategies_router
from .routers import strategy_doc as strategy_doc_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    await scheduler.start()
    await ib_watcher.start()
    try:
        yield
    finally:
        await ib_watcher.stop()
        await scheduler.stop()


app = FastAPI(title="aistock", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)
app.include_router(health_router.router)
app.include_router(strategies_router.router)
app.include_router(chat_router.router)
app.include_router(portfolio_router.router)
app.include_router(strategy_doc_router.router)
app.include_router(alerts_router.router)
app.include_router(schedules_router.router)
app.include_router(internal_router.router)


@app.get("/health")
def health():
    return {"ok": True}
