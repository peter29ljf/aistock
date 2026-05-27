#!/usr/bin/env python3
"""MCP: read/write the active strategy's portfolio.json."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from mcp.server.fastmcp import FastMCP
from _common import notify, strategy_id

from app import portfolio_io

mcp = FastMCP("portfolio")


@mcp.tool()
def list_positions() -> dict:
    """List all positions held under this strategy."""
    sid = strategy_id()
    return portfolio_io.load(sid)


@mcp.tool()
def add_position(symbol: str, buy_price: float, quantity: float, note: str = "") -> dict:
    """Add (or upsert) a position. symbol is auto-uppercased."""
    sid = strategy_id()
    pos = portfolio_io.add(sid, symbol, buy_price, quantity, note)
    notify(sid, "portfolio_changed", {"action": "add", "position": pos})
    return pos


@mcp.tool()
def update_position(symbol: str, buy_price: float | None = None,
                    quantity: float | None = None, note: str | None = None) -> dict:
    """Update fields of an existing position. Omit fields you don't want to change."""
    sid = strategy_id()
    updated = portfolio_io.update(sid, symbol, buy_price=buy_price, quantity=quantity, note=note)
    if updated is None:
        return {"error": f"position {symbol} not found"}
    notify(sid, "portfolio_changed", {"action": "update", "position": updated})
    return updated


@mcp.tool()
def remove_position(symbol: str) -> dict:
    """Remove a position by symbol."""
    sid = strategy_id()
    ok = portfolio_io.remove(sid, symbol)
    notify(sid, "portfolio_changed", {"action": "remove", "symbol": symbol.upper()})
    return {"ok": ok}


if __name__ == "__main__":
    mcp.run()
