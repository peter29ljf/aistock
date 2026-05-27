#!/usr/bin/env python3
"""MCP: subscribe / list / cancel price alerts via backend IB watcher."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP
from _common import api_delete, api_get, api_post, strategy_id

mcp = FastMCP("price-alert")


@mcp.tool()
def subscribe_price_alert(symbol: str, target_price: float, direction: str, note: str = "") -> dict:
    """Subscribe to a price alert. direction is 'above' or 'below'.
    When the symbol crosses target_price in that direction, a new Claude run is
    automatically spawned with trigger=alert. Returns {"alert_id": int}.
    """
    sid = strategy_id()
    return api_post("/_internal/alerts", {
        "sid": sid, "symbol": symbol, "target_price": target_price,
        "direction": direction, "note": note,
    })


@mcp.tool()
def list_alerts() -> dict:
    """List active alerts for this strategy."""
    rows = api_get("/_internal/alerts", {"sid": strategy_id()})
    return {"alerts": rows}


@mcp.tool()
def cancel_alert(alert_id: int) -> dict:
    """Cancel an active alert by id."""
    return api_delete(f"/_internal/alerts/{alert_id}")


if __name__ == "__main__":
    mcp.run()
