import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Schedule } from "../types";

function fmtNext(iso?: string) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function SchedulesSidebar({ sid, refreshKey }: { sid: string; refreshKey: number }) {
  const [items, setItems] = useState<Schedule[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      setItems(await api.listSchedules(sid));
      setErr("");
    } catch (e: any) {
      setErr(String(e.message ?? e));
    }
  }, [sid]);

  useEffect(() => { load(); }, [load, refreshKey]);

  return (
    <div className="sidebar-panel" style={{ flex: 1 }}>
      <div className="panel-head">
        <h3 style={{ margin: 0 }}>定时任务</h3>
      </div>
      {err && <div style={{ color: "#ff8a8a", fontSize: 12, marginBottom: 10 }}>{err}</div>}
      {items.length === 0 && !err && (
        <div className="empty">还没有定时任务。让 AI 用 schedule 工具添加。</div>
      )}
      <div className="rule-list">
        {items.map(t => {
          const next = fmtNext(t.next_run_time);
          const cronLabel = t.expr ?? (t.run_at ? `一次性 · ${t.run_at.slice(0, 16).replace("T", " ")}` : "");
          return (
            <div key={t.task_id} className="rule-card">
              <span className="rule-icon">⏰</span>
              <div className="rule-body">
                <div className="rule-title-row">
                  <span className="rule-name">{t.note || t.task_id}</span>
                  {cronLabel && <span className="rule-cron">{cronLabel}</span>}
                </div>
                {next && <div className="rule-meta">下次运行: {next}</div>}
              </div>
              <div className="rule-side">
                <span className="rule-status on">● 启用</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
