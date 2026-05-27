import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import ChatPanel from "../components/ChatPanel";
import type { Strategy } from "../types";

type HomeTab = "strategies" | "agent";

function relativeTime(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins}分钟前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}小时前`;
  return d.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

// ─── Strategies pane ─────────────────────────────────────────────────────────

function StrategiesPane() {
  const [items, setItems] = useState<Strategy[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const refresh = async () => {
    try { setItems(await api.listStrategies()); }
    catch (e: any) { setErr(String(e.message ?? e)); }
  };
  useEffect(() => { refresh(); }, []);

  const onCreate = async () => {
    if (!name.trim()) return;
    setBusy(true); setErr("");
    try { await api.createStrategy(name.trim(), description.trim()); setName(""); setDescription(""); await refresh(); }
    catch (e: any) { setErr(String(e.message ?? e)); }
    finally { setBusy(false); }
  };

  const onDelete = async (sid: string) => {
    if (!confirm(`删除策略 ${sid}? 文件夹与日志会被一并清除。`)) return;
    try { await api.deleteStrategy(sid); await refresh(); }
    catch (e: any) { setErr(String(e.message ?? e)); }
  };

  return (
    <div className="strategies-pane">
      <div className="new-form">
        <input placeholder="策略名称" value={name} onChange={e => setName(e.target.value)} />
        <input placeholder="一句话描述（可选）" value={description} onChange={e => setDescription(e.target.value)} style={{ flex: 1 }} />
        <button className="primary" disabled={busy || !name.trim()} onClick={onCreate}>新建策略</button>
      </div>
      {err && <p style={{ color: "#ff8a8a" }}>{err}</p>}
      <div className="strategy-list">
        {items.length === 0 && <div className="empty">还没有策略，新建一条开始。</div>}
        {items.map(s => (
          <div key={s.sid} className="strategy-card">
            <div>
              <Link to={`/s/${s.sid}`} style={{ fontWeight: 600, fontSize: 16 }}>{s.name ?? s.sid}</Link>
              <div className="meta">sid: {s.sid}{s.description ? ` · ${s.description}` : ""}{s.created_at ? ` · 创建于 ${s.created_at.slice(0, 19).replace("T", " ")}` : ""}</div>
            </div>
            <div className="row-actions">
              <Link to={`/s/${s.sid}`}><button>打开</button></Link>
              <button className="danger" onClick={() => onDelete(s.sid)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Agent pane ──────────────────────────────────────────────────────────────

function AgentPane() {
  const [sessions, setSessions] = useState<Strategy[]>([]);
  const [activeSid, setActiveSid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [listKey, setListKey] = useState(0);

  const loadSessions = async () => {
    try {
      const list = await api.listAgentSessions();
      // newest first
      setSessions([...list].reverse());
    } catch (e: any) { setErr(String(e.message ?? e)); }
  };

  useEffect(() => { loadSessions(); }, [listKey]);

  const onNew = async () => {
    setBusy(true); setErr("");
    try {
      const s = await api.createAgentSession();
      setListKey(k => k + 1);
      setActiveSid(s.sid);
    } catch (e: any) { setErr(String(e.message ?? e)); }
    finally { setBusy(false); }
  };

  const onDelete = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    if (!confirm("删除这条对话记录？")) return;
    try {
      await api.deleteAgentSession(sid);
      if (activeSid === sid) setActiveSid(null);
      setListKey(k => k + 1);
    } catch (e: any) { setErr(String(e.message ?? e)); }
  };

  const activeSession = sessions.find(s => s.sid === activeSid);

  return (
    <div className="agent-pane">
      <div className="agent-sidebar">
        <div className="agent-sidebar-header">
          <button className="primary new-conv-btn" disabled={busy} onClick={onNew}>
            {busy ? "创建中…" : "+ 新建对话"}
          </button>
          {err && <p style={{ color: "#ff8a8a", fontSize: 12, margin: "6px 0 0" }}>{err}</p>}
        </div>
        <div className="agent-session-list">
          {sessions.length === 0 && (
            <div className="agent-list-empty">暂无对话记录</div>
          )}
          {sessions.map(s => (
            <div
              key={s.sid}
              className={`agent-session-item${s.sid === activeSid ? " active" : ""}`}
              onClick={() => setActiveSid(s.sid)}
            >
              <div className="agent-session-row">
                <span className="agent-session-name">{s.name ?? s.sid}</span>
                <button
                  className="agent-del-btn"
                  title="删除"
                  onClick={(e) => onDelete(e, s.sid)}
                >×</button>
              </div>
              <div className="agent-session-time">{relativeTime(s.created_at)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="agent-chat">
        {activeSid ? (
          <ChatPanel
            key={activeSid}
            sid={activeSid}
            title={activeSession?.name}
          />
        ) : (
          <div className="agent-chat-empty">
            <div>选择左侧对话，或点击「+ 新建对话」开始</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── HomePage ─────────────────────────────────────────────────────────────────

export default function HomePage() {
  const [tab, setTab] = useState<HomeTab>("strategies");

  return (
    <div className="home-page">
      <div className="home-tabs-bar">
        <button
          className={`home-tab-btn${tab === "strategies" ? " active" : ""}`}
          onClick={() => setTab("strategies")}
        >策略</button>
        <button
          className={`home-tab-btn${tab === "agent" ? " active" : ""}`}
          onClick={() => setTab("agent")}
        >🤖 助手</button>
      </div>

      <div className="home-tab-content">
        <div className={`home-pane${tab === "strategies" ? " visible" : ""}`}>
          <StrategiesPane />
        </div>
        <div className={`home-pane agent-mode${tab === "agent" ? " visible" : ""}`}>
          <AgentPane />
        </div>
      </div>
    </div>
  );
}
