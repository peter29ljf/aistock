import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { ChatEvent } from "../types";

interface Props {
  sid: string;
  title?: string;
  onRefreshPortfolio?: () => void;
  onRefreshDoc?: () => void;
}

interface Msg {
  id: string;
  role: "user" | "assistant" | "tool" | "divider" | "system_event";
  text: string;
  toolName?: string;
  toolInput?: string;
  toolResult?: string;
}

function renderEvents(events: ChatEvent[]): Msg[] {
  const out: Msg[] = [];

  for (const ev of events) {
    // 用户手动发的消息 — 两种格式：
    // history: {kind:"user_message", content:"..."}
    // SSE:     {type:"user_message", entry:{kind:"user_message", content:"..."}}
    if (ev.kind === "user_message" && typeof ev.content === "string") {
      out.push({ id: `${out.length}-u`, role: "user", text: ev.content });
      continue;
    }
    if (ev.type === "user_message") {
      const entry = (ev as any).entry;
      const content = typeof entry?.content === "string" ? entry.content : "";
      if (content) out.push({ id: `${out.length}-u`, role: "user", text: content });
      continue;
    }
    // 系统触发事件（告警/定时）
    if (ev.kind === "alert") {
      const e = ev as any;
      out.push({ id: `${out.length}-ev`, role: "system_event",
        text: `⚡ 价格告警: ${e.symbol} ${e.dir === "above" ? "突破" : "跌破"} $${e.target}` });
      continue;
    }
    if (ev.kind === "schedule") {
      out.push({ id: `${out.length}-ev`, role: "system_event",
        text: `⏰ 定时任务: ${(ev as any).note || "已触发"}` });
      continue;
    }
    // Claude run 开始分割线
    if (ev.type === "run_started") {
      const trigger = (ev as any).trigger ?? "user";
      const label = ({ user: "对话", alert: "告警触发", schedule: "定时触发" } as Record<string, string>)[trigger] ?? trigger;
      out.push({ id: `${out.length}-div`, role: "divider", text: label });
      continue;
    }
    // AI 回复
    if (ev.type === "assistant") {
      const blocks: any[] = Array.isArray((ev as any).message?.content) ? (ev as any).message.content : [];
      for (const b of blocks) {
        if (b.type === "text" && b.text?.trim()) {
          const last = out[out.length - 1];
          if (last?.role === "assistant") {
            last.text += b.text;
          } else {
            out.push({ id: `${out.length}-a`, role: "assistant", text: b.text });
          }
        } else if (b.type === "tool_use") {
          const inp = JSON.stringify(b.input ?? {});
          out.push({
            id: `${out.length}-t`, role: "tool", text: "",
            toolName: b.name,
            toolInput: inp.length > 500 ? inp.slice(0, 500) + "…" : inp,
          });
        }
      }
      continue;
    }
    // 工具结果 — 附加到最近的 tool 消息
    if (ev.type === "user") {
      const blocks: any[] = Array.isArray((ev as any).message?.content) ? (ev as any).message.content : [];
      for (const b of blocks) {
        if (b.type === "tool_result") {
          const content = typeof b.content === "string" ? b.content : JSON.stringify(b.content);
          for (let i = out.length - 1; i >= 0; i--) {
            if (out[i].role === "tool" && out[i].toolResult === undefined) {
              out[i] = { ...out[i], toolResult: content.slice(0, 1200) };
              break;
            }
          }
        }
      }
      continue;
    }
    // 错误
    if (ev.type === "error" && (ev as any).message) {
      out.push({ id: `${out.length}-err`, role: "system_event", text: `⚠ ${(ev as any).message}` });
    }
  }
  return out;
}

function ToolMsg({ m }: { m: Msg }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tool-block">
      <button className="tool-header" onClick={() => setOpen(o => !o)}>
        <span className="tool-icon">⚙</span>
        <span className="tool-name">{m.toolName}</span>
        <span className="tool-status">{m.toolResult !== undefined ? "✓" : "…"}</span>
        <span className="tool-toggle">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="tool-detail">
          <div className="tool-section-label">参数</div>
          <pre className="tool-code">{m.toolInput}</pre>
          {m.toolResult !== undefined && (
            <>
              <div className="tool-section-label">结果</div>
              <pre className="tool-code result">{m.toolResult}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatPanel({ sid, title, onRefreshPortfolio, onRefreshDoc }: Props) {
  const [events, setEvents] = useState<ChatEvent[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.loadHistory(sid).then(h => { if (!cancelled) setEvents(h); });
    const es = new EventSource(`/api/strategies/${sid}/chat/stream`);
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data);
        setEvents(prev => [...prev, ev]);
        if (ev.type === "run_started") setStreaming(true);
        if (ev.type === "done") setStreaming(false);
        if (ev.type === "portfolio_changed") onRefreshPortfolio?.();
        if (ev.type === "strategy_doc_changed") onRefreshDoc?.();
      } catch {}
    };
    es.onerror = () => {};
    return () => { cancelled = true; es.close(); };
  }, [sid]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const messages = useMemo(() => renderEvents(events), [events]);

  const onSend = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setSending(true);
    try {
      await api.sendMessage(sid, msg);
      setInput("");
      inputRef.current?.focus();
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-sid">{title ?? sid}</span>
        <span className={`chat-status${streaming ? " active" : ""}`}>
          {streaming ? "● Claude 思考中…" : "○ 待命"}
        </span>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">还没有消息，输入下方开始对话。</div>
        )}
        {messages.map(m => {
          if (m.role === "divider") {
            return (
              <div key={m.id} className="chat-divider">
                <span>{m.text}</span>
              </div>
            );
          }
          if (m.role === "system_event") {
            return <div key={m.id} className="chat-system-event">{m.text}</div>;
          }
          if (m.role === "tool") {
            return <ToolMsg key={m.id} m={m} />;
          }
          return (
            <div key={m.id} className={`chat-bubble ${m.role}`}>
              {m.role === "assistant" && <div className="bubble-label">Claude</div>}
              <div className="bubble-text">{m.text}</div>
            </div>
          );
        })}
        {streaming && (
          <div className="chat-typing">
            <span /><span /><span />
          </div>
        )}
      </div>

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          value={input}
          placeholder="对 Claude 说点什么… (Ctrl+Enter 发送)"
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") onSend(); }}
          rows={3}
        />
        <button className="primary send-btn" disabled={sending || !input.trim()} onClick={onSend}>
          {sending ? "发送中" : "发送"}
        </button>
      </div>
    </div>
  );
}
