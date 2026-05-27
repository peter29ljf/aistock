# aistock

An AI autonomous trading console powered by Claude Code. Each strategy runs as an independent Claude Code agent that interacts with a real brokerage account via MCP tools.

## Features

- **Strategy Management** — Run multiple strategies in parallel, each with its own chat, strategy doc, and portfolio record
- **Assistant Chat** — Standalone AI assistant tab for market queries and configuration
- **Real-time Quotes** — Full-session support including pre-market / post-market / overnight (yfinance), with optional IB Gateway live feed
- **Price Alerts** — Set price breakout/breakdown alerts that automatically trigger Claude to execute the strategy
- **Scheduled Tasks** — Cron-based automatic strategy execution
- **Options Analysis** — OI support/resistance, Max Pain, PCR (via Tiger Brokers API)
- **Live Order Execution** — Place limit / market / stop / trailing-stop orders via Tiger Brokers OpenAPI, full-session supported

## Architecture

```
frontend/          React + Vite UI
backend/           FastAPI backend
  app/
    routers/       API routes (strategies / agent / chat / alerts / schedules …)
    claude_runner  Spawns claude CLI in stream-json mode
    ib_watcher     IB Gateway real-time quote subscription
    scheduler      APScheduler cron jobs
mcp_servers/       MCP tool servers
  yfinance_tools/  Real-time quotes + K-lines + technical indicators
  portfolio/       Strategy portfolio CRUD
  strategy_doc/    Strategy document read/write
  price_alert/     Price alert management
  scheduler/       Scheduled task management
strategies/        One directory per strategy (CLAUDE.md + strategy.md + logs)
```

## Initial Setup

### 1. Tiger Brokers Credentials

Download the `.properties` config file from the [Tiger Brokers developer portal](https://quant.itigerup.com) and save it locally (e.g. `~/.tiger/openapi.properties`).

Specify the path via the `AISTOCK_TIGER_CONFIG` environment variable, or reference it directly inside the auto-generated `.mcp.json` files under each strategy directory.

> ⚠️ The `.properties` file contains your Tiger private key — **never commit it to git** (already covered by `.gitignore`).

### 2. Claude Code CLI

Make sure the Claude Code CLI is installed:

```bash
claude --version
# Default path: ~/.local/bin/claude
# Override with AISTOCK_CLAUDE_BIN if installed elsewhere
```

### 3. Internal Token (auto-generated)

On first startup the backend writes a random token to `data/internal_token`. This token is used to authenticate MCP servers calling back into the backend. The file is excluded by `.gitignore` and **must not be committed**.

### 4. Strategy `.mcp.json` (auto-generated)

When a strategy is created, the backend generates a `.mcp.json` in that strategy's directory containing the `internal_token` and MCP server paths. This file is excluded by `.gitignore` and **must not be committed**.

---

## Running Locally

```bash
# 1. Install backend dependencies
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start the backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop asyncio

# 3. Start the frontend
cd frontend && npm install && npm run dev
```

Visit http://127.0.0.1:5173

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AISTOCK_CLAUDE_BIN` | `~/.local/bin/claude` | Path to the claude CLI binary |
| `AISTOCK_TIGER_CONFIG` | — | Path to the Tiger Brokers `.properties` file |
| `AISTOCK_IB_HOST` | `127.0.0.1` | IB Gateway host |
| `AISTOCK_IB_PORT` | `4001` | IB Gateway port (4001 = live, 7497 = paper) |
| `AISTOCK_API_HOST` | `127.0.0.1` | Backend bind address |
| `AISTOCK_API_PORT` | `8000` | Backend port |

## How CLAUDE.md Works

Each strategy directory contains a `CLAUDE.md` that the Claude Code agent reads on every invocation:

- **Context rebuild**: reads `strategy.md` (strategy spec), `portfolio.json` (live positions), and the tail of today's chat log
- **Trigger types**: `trigger=user` (user message), `trigger=alert` (price alert fired), `trigger=schedule` (cron task)
- **Available tools**: tiger-openapi (options / orders / account), yfinance-tools (quotes / K-lines / indicators), portfolio, strategy-doc, price-alert, scheduler

The file is auto-generated when a strategy is created and can be edited manually to adjust agent behavior. The **Assistant** tab uses a lighter variant with no order-placement capability (requires explicit user confirmation to trade).

## Dependencies

- [Claude Code CLI](https://claude.ai/code) — AI agent runtime
- [Tiger Brokers OpenAPI](https://quant.itigerup.com) — Live quotes and order execution (subscription required)
- IB Gateway (optional) — IBKR real-time quote feed

## Warning

⚠️ This project connects to a real brokerage account. All orders placed are live trades. Use with caution.
