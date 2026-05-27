from __future__ import annotations

import aiosqlite
from typing import Any

from .config import ALERTS_DB_PATH, DATA_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sid TEXT NOT NULL,
  symbol TEXT NOT NULL,
  target REAL NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('above','below')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','fired','cancelled')),
  note TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  fired_at TEXT,
  fired_price REAL
);
CREATE INDEX IF NOT EXISTS alerts_active ON alerts(status, symbol);
"""


async def init() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def create(sid: str, symbol: str, target: float, direction: str, note: str = "") -> int:
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO alerts(sid,symbol,target,direction,note) VALUES (?,?,?,?,?)",
            (sid, symbol.upper(), target, direction, note),
        )
        await db.commit()
        return cur.lastrowid or 0


async def list_active(sid: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT id,sid,symbol,target,direction,status,note,created_at,fired_at,fired_price FROM alerts WHERE status='active'"
    args: tuple = ()
    if sid:
        sql += " AND sid=?"
        args = (sid,)
    sql += " ORDER BY id"
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, args)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def list_for_strategy(sid: str) -> list[dict[str, Any]]:
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id,sid,symbol,target,direction,status,note,created_at,fired_at,fired_price"
            " FROM alerts WHERE sid=? ORDER BY id DESC LIMIT 200",
            (sid,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def cancel(alert_id: int) -> bool:
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        cur = await db.execute(
            "UPDATE alerts SET status='cancelled' WHERE id=? AND status='active'", (alert_id,)
        )
        await db.commit()
        return (cur.rowcount or 0) > 0


async def mark_fired(alert_id: int, price: float) -> dict[str, Any] | None:
    async with aiosqlite.connect(ALERTS_DB_PATH) as db:
        await db.execute(
            "UPDATE alerts SET status='fired', fired_at=datetime('now'), fired_price=? WHERE id=? AND status='active'",
            (price, alert_id),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM alerts WHERE id=?", (alert_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
