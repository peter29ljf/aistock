import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Alert } from "../types";

export default function AlertsSidebar({ sid, refreshKey }: { sid: string; refreshKey: number }) {
  const [items, setItems] = useState<Alert[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      setItems(await api.listAlerts(sid));
      setErr("");
    } catch (e: any) {
      setErr(String(e.message ?? e));
    }
  }, [sid]);

  useEffect(() => { load(); }, [load, refreshKey]);

  return (
    <div className="sidebar-panel" style={{ flex: 1 }}>
      <div className="panel-head">
        <h3 style={{ margin: 0 }}>价格警报</h3>
      </div>
      {err && <div style={{ color: "#ff8a8a", fontSize: 12, marginBottom: 10 }}>{err}</div>}
      {items.length === 0 && !err && (
        <div className="empty">还没有价格警报。让 AI 用 alert 工具添加。</div>
      )}
      <div className="rule-list">
        {items.map(a => {
          const isUp = a.direction === "above";
          const fired = a.status === "fired";
          const active = a.status === "active";
          return (
            <div key={a.id} className={`rule-card${active ? "" : " off"}`}>
              <span className="rule-icon">⚡</span>
              <div className="rule-body">
                <div className="rule-title-row">
                  <span className="rule-name">{a.symbol}</span>
                  <span className={`alert-cond ${isUp ? "up" : "down"}`}>
                    {isUp ? "突破" : "跌破"} ${a.target.toFixed(2)}
                  </span>
                </div>
                {a.note && <div className="rule-action">{a.note}</div>}
                {fired && a.fired_price != null && (
                  <div className="rule-meta">
                    触发价: ${a.fired_price.toFixed(2)}{a.fired_at ? ` · ${a.fired_at.slice(0, 16).replace("T", " ")}` : ""}
                  </div>
                )}
              </div>
              <div className="rule-side">
                <span className={`rule-status${fired ? " fired" : active ? " on" : ""}`}>
                  {fired ? "✓ 已触发" : active ? "● 监控中" : "○ 已取消"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
