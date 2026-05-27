#!/usr/bin/env python3
"""MCP: read/update the active strategy's strategy.md."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from mcp.server.fastmcp import FastMCP
from _common import notify, strategy_id

from app import strategy_doc_io

mcp = FastMCP("strategy-doc")


@mcp.tool()
def read_strategy() -> dict:
    """Read the authoritative strategy markdown for this strategy."""
    sid = strategy_id()
    return {"markdown": strategy_doc_io.read(sid)}


@mcp.tool()
def update_strategy(markdown: str) -> dict:
    """Replace the strategy markdown completely."""
    sid = strategy_id()
    strategy_doc_io.write(sid, markdown)
    notify(sid, "strategy_doc_changed", {"action": "write"})
    return {"ok": True, "length": len(markdown)}


@mcp.tool()
def append_strategy(text: str) -> dict:
    """Append a paragraph or section to the strategy markdown."""
    sid = strategy_id()
    strategy_doc_io.append(sid, text)
    notify(sid, "strategy_doc_changed", {"action": "append"})
    return {"ok": True}


if __name__ == "__main__":
    mcp.run()
