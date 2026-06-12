# aistock — Codex 项目上下文

AI 自主交易控制台。FastAPI 后端 + React 前端，每条策略对应一个 Codex agent，通过 MCP 工具与 Tiger Brokers 真实账户交互。

## 安全约束（最高优先级）

- Tiger 账户是 **真实实盘（env=PROD）**，资金操作不可逆
- Codex 开发辅助时**严禁直接下单**，下单只能通过策略 AI agent 执行
- `data/internal_token`、`*.properties`、`strategies/*/.mcp.json` 含敏感凭证，绝不提交

## 目录结构

```
backend/app/
  main.py            FastAPI 入口，lifespan 启动 ib_watcher + scheduler
  routers/           API 路由（strategies, agent, chat, alerts, schedules, market）
  claude_runner.py   以 stream-json 调起 Codex CLI
  strategies.py      策略/agent会话 CRUD（文件系统存储在 strategies/）
  market_data.py     yfinance 行情封装（fix: index.name=None → reset_index → "index"列）
  ib_watcher.py      IB Gateway 实时行情订阅（ib_insync）
  scheduler.py       APScheduler 定时任务

mcp_servers/
  yfinance_tools/    行情+K线+技术指标+get_stock_quote（全时段盘前/盘后）
  portfolio/         策略持仓 CRUD
  strategy_doc/      策略文档读写
  price_alert/       价格告警管理
  scheduler/         定时任务管理

strategies/<sid>/
  AGENTS.md          agent 行为指令（后端自动生成）
  strategy.md        策略权威描述（可手动编辑）
  portfolio.json     真实持仓（MCP 工具读写，不提交）
  .mcp.json          MCP 服务器配置含 token（自动生成，不提交）
  logs/              每日 chat 日志 jsonl（不提交）

frontend/src/
  pages/HomePage.tsx   两 Tab：策略列表 / 助手对话
  pages/StrategyPage.tsx  四 Tab：聊天 / 策略文档 / 持仓 / 告警+定时
  components/ChatPanel.tsx  SSE 消息流 + 发送框
```

## 运行

```bash
# 后端
cd backend && source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop asyncio

# 前端
cd frontend && npm run dev
```

## 关键设计决策

- **策略存储**：文件系统（`strategies/<sid>/`），无数据库
- **agent 会话**：复用策略基础设施，`_meta.json` 中 `kind=agent` 区分
- **SSE 格式**：历史消息 `{kind:"user_message"}` vs 实时 `{type:"user_message", entry:{...}}`
- **yfinance 1.2.0**：`raw.index.name = None`，`reset_index()` 产生 `"index"` 列而非 `"Date"`
- **Tiger 下单**：工厂函数（`limit_order` 等）不接受 `outside_rth`/`trading_session_type`，需在 Order 对象上手动赋值

## 外部依赖

- Tiger MCP: `github.com/peter29ljf/tigermcp`（同 `~/workspace/tigerskill/tiger-mcp-server/`）
- Codex CLI: `~/.local/bin/Codex`（可通过 `AISTOCK_CLAUDE_BIN` 覆盖）
