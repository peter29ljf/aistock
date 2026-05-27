import { useCallback, useEffect, useState } from "react";

export default function StrategyDocSidebar({ sid, refreshKey }: { sid: string; refreshKey: number }) {
  const [markdown, setMarkdown] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/strategies/${sid}/strategy`);
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setMarkdown(d.markdown || "");
      setErr("");
    } catch (e: any) { setErr(String(e.message ?? e)); }
  }, [sid]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const save = async () => {
    try {
      const r = await fetch(`/api/strategies/${sid}/strategy`, {
        method: "PUT", headers: { "content-type": "application/json" },
        body: JSON.stringify({ markdown: draft }),
      });
      if (!r.ok) throw new Error(await r.text());
      setMarkdown(draft);
      setEditing(false);
    } catch (e: any) { setErr(String(e.message ?? e)); }
  };

  return (
    <div className="sidebar-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>策略描述</h3>
        {!editing ? (
          <button onClick={() => { setDraft(markdown); setEditing(true); }}>编辑</button>
        ) : (
          <span style={{ display: "flex", gap: 6 }}>
            <button className="primary" onClick={save}>保存</button>
            <button onClick={() => setEditing(false)}>取消</button>
          </span>
        )}
      </div>
      {err && <div style={{ color: "#ff8a8a", fontSize: 12 }}>{err}</div>}
      {!editing ? (
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, color: "#cfd6e1", marginTop: 10 }}>
          {markdown || <span className="empty">空。让 AI 用 strategy-doc 工具填写。</span>}
        </pre>
      ) : (
        <textarea
          value={draft}
          onChange={e => setDraft(e.target.value)}
          style={{ width: "100%", minHeight: 240, marginTop: 10 }}
        />
      )}
    </div>
  );
}
