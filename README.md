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

## 初次配置

### 1. Tiger Brokers 凭证文件

从 [Tiger Brokers 开发者后台](https://quant.itigerup.com) 下载 `.properties` 配置文件，保存到本地任意位置（如 `~/.tiger/openapi.properties`）。

在后端配置中指定路径（`AISTOCK_TIGER_CONFIG` 环境变量或直接在 `mcp_servers/` 各服务的 `.mcp.json` 中引用）。

> ⚠️ `.properties` 文件包含 Tiger 私钥，**严禁提交到 git**（已加入 `.gitignore`）。

### 2. Claude Code CLI

确认已安装 Claude Code CLI：

```bash
claude --version
# 默认路径: ~/.local/bin/claude
# 可通过 AISTOCK_CLAUDE_BIN 环境变量指定其他路径
```

### 3. 内部 Token（自动生成）

后端首次启动时会在 `data/internal_token` 自动生成随机 token，用于 MCP 服务器与后端通信鉴权。该文件已在 `.gitignore` 中排除，**不会提交到 git**。

### 4. 策略 .mcp.json（自动生成）

每条策略目录下的 `.mcp.json` 由后端在创建策略时自动生成，内含 `internal_token` 和各 MCP 服务器路径。该文件已在 `.gitignore` 中排除，**不会提交到 git**。

---

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
| `AISTOCK_TIGER_CONFIG` | — | Tiger Brokers `.properties` 文件路径 |
| `AISTOCK_IB_HOST` | `127.0.0.1` | IB Gateway 地址 |
| `AISTOCK_IB_PORT` | `4001` | IB Gateway 端口（4001=live, 7497=paper） |
| `AISTOCK_API_HOST` | `127.0.0.1` | 后端绑定地址 |
| `AISTOCK_API_PORT` | `8000` | 后端端口 |

## CLAUDE.md 说明

每条策略目录下有一个 `CLAUDE.md`，这是 Claude Code agent 每次被唤醒时读取的行为指令：

- **上下文重建**：读 `strategy.md`（策略描述）、`portfolio.json`（真实持仓）、今日 chat log 末尾
- **触发类型**：`trigger=user`（用户对话）、`trigger=alert`（价格告警）、`trigger=schedule`（定时任务）
- **可用工具**：tiger-openapi（期权/下单/账户）、yfinance-tools（行情/K线/指标）、portfolio、strategy-doc、price-alert、scheduler

该文件由后端创建策略时自动生成，也可手动编辑以调整 agent 行为。`助手对话` Tab 中的 agent 会话使用精简版 CLAUDE.md（无下单功能，需用户二次确认）。

## 依赖

- [Claude Code CLI](https://claude.ai/code) — AI agent 运行时
- [Tiger Brokers OpenAPI](https://quant.itigerup.com) — 实盘行情与下单（需开通）
- IB Gateway（可选）— IBKR 实时行情推送

## 注意

⚠️ 此项目连接真实交易账户，所有下单操作均为实盘，请谨慎使用。
