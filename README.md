# aistock

基于 Claude Code 的 AI 自主交易控制台。每条策略对应一个独立的 Claude Code agent，通过 MCP 工具与真实券商账户交互。

## 功能

- **策略管理** — 多策略并行，每条策略有独立聊天、策略文档、持仓记录
- **助手对话** — 独立 AI 助手页面，用于市场查询、功能配置
- **实时行情** — 支持盘前/盘后/夜盘全时段（yfinance），可接 IB Gateway 实时推送
- **价格告警** — 设定价格突破/跌破告警，自动唤起 Claude 执行策略
- **定时任务** — Cron 触发策略自动运行
- **期权分析** — OI 支撑压力、Max Pain、PCR（通过 Tiger Brokers API）
- **实盘下单** — 通过 Tiger Brokers OpenAPI 下限价/市价/止损/跟踪止损单，支持全时段

## 架构

```
frontend/          React + Vite UI
backend/           FastAPI 后端
  app/
    routers/       API 路由（strategies / agent / chat / alerts / schedules …）
    claude_runner  以 stream-json 模式调起 claude CLI
    ib_watcher     IB Gateway 实时行情订阅
    scheduler      APScheduler 定时任务
mcp_servers/       各 MCP 工具服务
  yfinance_tools/  实时报价 + K线 + 技术指标
  portfolio/       策略持仓 CRUD
  strategy_doc/    策略文档读写
  price_alert/     价格告警管理
  scheduler/       定时任务管理
strategies/        每条策略目录（CLAUDE.md + strategy.md + 日志）
```

## 本地启动

```bash
# 1. 安装后端依赖
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 启动后端
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop asyncio

# 3. 启动前端
cd frontend && npm install && npm run dev
```

访问 http://127.0.0.1:5173

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `AISTOCK_CLAUDE_BIN` | `~/.local/bin/claude` | claude CLI 路径 |
| `AISTOCK_IB_HOST` | `127.0.0.1` | IB Gateway 地址 |
| `AISTOCK_IB_PORT` | `4001` | IB Gateway 端口（4001=live, 7497=paper） |
| `AISTOCK_API_HOST` | `127.0.0.1` | 后端绑定地址 |
| `AISTOCK_API_PORT` | `8000` | 后端端口 |

## 依赖

- [Claude Code CLI](https://claude.ai/code) — AI agent 运行时
- [Tiger Brokers OpenAPI](https://quant.itigerup.com) — 实盘行情与下单（需开通）
- IB Gateway（可选）— IBKR 实时行情推送

## 注意

⚠️ 此项目连接真实交易账户，所有下单操作均为实盘，请谨慎使用。
