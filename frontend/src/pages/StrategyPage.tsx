import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AlertsSidebar from "../components/AlertsSidebar";
import ChatPanel from "../components/ChatPanel";
import PortfolioSidebar from "../components/PortfolioSidebar";
import SchedulesSidebar from "../components/SchedulesSidebar";
import StrategyDocSidebar from "../components/StrategyDocSidebar";

type Tab = "chat" | "strategy" | "portfolio" | "schedules" | "alerts";

const TABS: { key: Tab; label: string }[] = [
  { key: "chat",      label: "💬 聊天" },
  { key: "strategy",  label: "📋 策略描述" },
  { key: "portfolio", label: "📈 持仓" },
  { key: "schedules", label: "⏰ 定时任务" },
  { key: "alerts",    label: "⚡ 价格警报" },
];

export default function StrategyPage() {
  const { sid = "" } = useParams();
  const navigate = useNavigate();
  const [portfolioKey, setPortfolioKey] = useState(0);
  const [docKey, setDocKey] = useState(0);
  const [alertsKey, setAlertsKey] = useState(0);
  const [schedulesKey, setSchedulesKey] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="strategy-page">
      <div className="tab-bar">
        <button className="back-btn" onClick={() => navigate(-1)}>←</button>
        <span className="sid-label">{sid}</span>
        {TABS.map(t => (
          <button
            key={t.key}
            className={`tab-btn${activeTab === t.key ? " active" : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {/* 保持挂载，用 display 切换，维持 SSE 连接和状态 */}
        <div className={`tab-pane${activeTab === "chat" ? " visible" : ""}`}>
          <ChatPanel
            sid={sid}
            onRefreshPortfolio={() => setPortfolioKey(k => k + 1)}
            onRefreshDoc={() => setDocKey(k => k + 1)}
            onRefreshAlerts={() => setAlertsKey(k => k + 1)}
            onRefreshSchedules={() => setSchedulesKey(k => k + 1)}
          />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "strategy" ? " visible" : ""}`}>
          <StrategyDocSidebar sid={sid} refreshKey={docKey} />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "portfolio" ? " visible" : ""}`}>
          <PortfolioSidebar sid={sid} refreshKey={portfolioKey} />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "schedules" ? " visible" : ""}`}>
          <SchedulesSidebar sid={sid} refreshKey={schedulesKey} />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "alerts" ? " visible" : ""}`}>
          <AlertsSidebar sid={sid} refreshKey={alertsKey} />
        </div>
      </div>
    </div>
  );
}
