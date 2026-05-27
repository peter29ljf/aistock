from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import STRATEGIES_DIR, MCP_SERVERS_DIR, ROOT, API_BASE, VENV_PYTHON, internal_token

_SID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
_META_NAME = "_meta.json"


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or datetime.now().strftime("s-%Y%m%d-%H%M%S")


def _unique_sid(base: str) -> str:
    sid = base
    i = 2
    while (STRATEGIES_DIR / sid).exists():
        sid = f"{base}-{i}"
        i += 1
    return sid


def list_strategies(kind: str = "strategy") -> list[dict[str, Any]]:
    if not STRATEGIES_DIR.exists():
        return []
    out = []
    for d in sorted(STRATEGIES_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / _META_NAME
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                meta = {}
        if meta.get("kind", "strategy") != kind:
            continue
        out.append({"sid": d.name, **meta})
    return out


def get_strategy(sid: str) -> dict[str, Any] | None:
    d = STRATEGIES_DIR / sid
    if not d.is_dir():
        return None
    meta_path = d / _META_NAME
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            pass
    return {"sid": sid, **meta}


def create_strategy(name: str, description: str = "") -> dict[str, Any]:
    base = _slugify(name)
    if not _SID_RE.match(base):
        base = datetime.now().strftime("s-%Y%m%d-%H%M%S")
    sid = _unique_sid(base)
    d = STRATEGIES_DIR / sid
    (d / "logs").mkdir(parents=True, exist_ok=True)

    (d / "strategy.md").write_text(
        f"# {name}\n\n{description}\n\n"
        "> 由 AI 自主维护。每轮决策前先 read_strategy，按需 update_strategy。\n",
        encoding="utf-8",
    )
    (d / "portfolio.json").write_text(json.dumps({"positions": []}, indent=2), encoding="utf-8")

    _write_mcp_json(d, sid)
    _write_claude_md(d, sid, name)

    meta = {
        "name": name,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (d / _META_NAME).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"sid": sid, **meta}


def delete_strategy(sid: str) -> bool:
    d = STRATEGIES_DIR / sid
    if not d.is_dir():
        return False
    shutil.rmtree(d)
    return True


def _write_mcp_json(strategy_dir: Path, sid: str) -> None:
    token = internal_token()
    aistock_root = str(ROOT)
    config = {
        "mcpServers": {
            "tiger-openapi": {
                "type": "stdio",
                "command": "python3",
                "args": [
                    "/Users/junfenglin/workspace/tigerskill/tiger-mcp-server/server.py",
                    "--config",
                    "/Users/junfenglin/workspace/tigerskill/tiger_openapi_config.properties",
                ],
                "env": {},
            },
            "portfolio": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "portfolio" / "server.py")],
                "env": {
                    "AISTOCK_ROOT": aistock_root,
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
            "strategy-doc": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "strategy_doc" / "server.py")],
                "env": {
                    "AISTOCK_ROOT": aistock_root,
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
            "yfinance-tools": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "yfinance_tools" / "server.py")],
                "env": {"AISTOCK_ROOT": aistock_root, "STRATEGY_ID": sid},
            },
            "price-alert": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "price_alert" / "server.py")],
                "env": {
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
            "scheduler": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "scheduler" / "server.py")],
                "env": {
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
        }
    }
    (strategy_dir / ".mcp.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def create_agent_session(name: str = "") -> dict[str, Any]:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    sid = _unique_sid(f"agent-{ts}")
    d = STRATEGIES_DIR / sid
    (d / "logs").mkdir(parents=True, exist_ok=True)
    _write_agent_mcp_json(d, sid)
    _write_agent_claude_md(d, sid)
    auto_name = name.strip() or f"对话 {datetime.now().strftime('%m/%d %H:%M')}"
    meta = {
        "name": auto_name,
        "kind": "agent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (d / _META_NAME).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"sid": sid, **meta}


def _write_agent_mcp_json(strategy_dir: Path, sid: str) -> None:
    token = internal_token()
    aistock_root = str(ROOT)
    config = {
        "mcpServers": {
            "tiger-openapi": {
                "type": "stdio",
                "command": "python3",
                "args": [
                    "/Users/junfenglin/workspace/tigerskill/tiger-mcp-server/server.py",
                    "--config",
                    "/Users/junfenglin/workspace/tigerskill/tiger_openapi_config.properties",
                ],
                "env": {},
            },
            "yfinance-tools": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "yfinance_tools" / "server.py")],
                "env": {"AISTOCK_ROOT": aistock_root, "STRATEGY_ID": sid},
            },
            "price-alert": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "price_alert" / "server.py")],
                "env": {
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
            "scheduler": {
                "type": "stdio",
                "command": VENV_PYTHON,
                "args": [str(MCP_SERVERS_DIR / "scheduler" / "server.py")],
                "env": {
                    "STRATEGY_ID": sid,
                    "AISTOCK_API": API_BASE,
                    "AISTOCK_TOKEN": token,
                },
            },
        }
    }
    (strategy_dir / ".mcp.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def _write_agent_claude_md(strategy_dir: Path, sid: str) -> None:
    body = f"""# AI 助手 `{sid}`

你是 aistock 系统的 AI 投资助手。每次被唤醒都是无状态的，通过工具获取最新数据。

## 触发类型
- `trigger=user` → chat log 最后一条 role=user 是用户最新输入

## 可用工具
- `tiger-openapi`：账户/持仓/期权链/OI分析/市场状态（⚠️ 实盘，下单须用户明确二次确认）
- `yfinance-tools`：实时报价（全时段盘前/盘后）/ K 线 / 技术指标（MA/RSI/Bollinger/KDJ）
- `price-alert`：设置/查询/取消价格告警
- `scheduler`：设置/查询/取消定时任务

## 行为原则
- 用中文回答，简洁清晰
- 查询市场数据优先用 yfinance-tools（支持盘前盘后，无需订阅）
- 不主动下单，如需下单须用户明确确认后方可执行
- 每次对话结束后给出简洁的操作摘要
"""
    (strategy_dir / "CLAUDE.md").write_text(body, encoding="utf-8")


def _write_claude_md(strategy_dir: Path, sid: str, name: str) -> None:
    body = f"""# 策略 `{sid}` — {name}

你是这条策略的自主交易代理。每次被 spawn 都是无状态的，必须自行重建上下文。

## 启动后必做（按顺序）
1. 读 `strategy.md` — 策略权威描述
2. 读 `portfolio.json` — 真实持仓
3. 读 `logs/chat-<today>.jsonl` 末尾若干条 — 最近对话与系统事件

## 触发类型（看 `-p` 传入）
- `trigger=user` → chat log 最后一条 role=user 是用户最新输入；正常对话/决策
- `trigger=alert symbol=X target=Y dir=above|below alert_id=N` → 价格越线，按策略决定是否下单
- `trigger=schedule task_id=N note=...` → 定时任务到点，按策略执行

## 工具一览
- `tiger-openapi`：期权链/OI分析/账户/持仓/下单/撤单/市场状态（⚠️ 实盘）
- `yfinance-tools`：实时报价（全时段盘前/盘后）/ K 线 / 技术指标（MA/RSI/Bollinger/KDJ）
- `portfolio`：list/add/update/remove 持仓
- `strategy-doc`：read/update/append 策略文档
- `price-alert`：subscribe/list/cancel 价格告警
- `scheduler`：schedule_task(cron) / schedule_once / list / cancel

## 输出原则
- 决策结论用纯文本回答即可（会自动写回 chat log）
- 修改持仓/策略 必须走对应 MCP 工具，不要直接编辑 json/md
- 实盘下单前，把理由清楚说明
"""
    (strategy_dir / "CLAUDE.md").write_text(body, encoding="utf-8")
