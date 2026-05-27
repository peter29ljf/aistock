import { useCallback, useEffect, useState } from "react";
import type { Position } from "../types";

export default function PortfolioSidebar({ sid, refreshKey }: { sid: string; refreshKey: number }) {
  const [items, setItems] = useState<Position[]>([]);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await fetch(`/api/strategies/${sid}/portfolio`);
      if (!r.ok) throw new Error(await r.text());
      setItems(await r.json());
      setErr("");
    } catch (e: any) {
      setErr(String(e.message ?? e));
    }
  }, [sid]);

  useEffect(() => { load(); }, [load, refreshKey]);

  return (
    <div className="sidebar-panel" style={{ flex: 1 }}>
      <h3>持仓</h3>
      {err && <div style={{ color: "#ff8a8a", fontSize: 12 }}>{err}</div>}
      {items.length === 0 && <div className="empty">空。让 AI 用 portfolio 工具添加。</div>}
      {items.length > 0 && (
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ color: "#8a96a8" }}>
              <th style={{ textAlign: "left" }}>Sym</th>
              <th style={{ textAlign: "right" }}>买入</th>
              <th style={{ textAlign: "right" }}>现价</th>
              <th style={{ textAlign: "right" }}>数量</th>
              <th style={{ textAlign: "right" }}>盈亏</th>
            </tr>
          </thead>
          <tbody>
            {items.map(p => {
              const pnl = p.pnl_pct;
              const color = pnl == null ? "#e6e6e6" : pnl >= 0 ? "#8acc8a" : "#ff8a8a";
              return (
                <tr key={p.symbol}>
                  <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                  <td style={{ textAlign: "right" }}>{p.buy_price.toFixed(2)}</td>
                  <td style={{ textAlign: "right" }}>{p.current_price != null ? p.current_price.toFixed(2) : "—"}</td>
                  <td style={{ textAlign: "right" }}>{p.quantity}</td>
                  <td style={{ textAlign: "right", color }}>
                    {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
