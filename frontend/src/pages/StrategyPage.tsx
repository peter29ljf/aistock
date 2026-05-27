import { useState } from "react";
import { useParams } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import PortfolioSidebar from "../components/PortfolioSidebar";
import StrategyDocSidebar from "../components/StrategyDocSidebar";

type Tab = "chat" | "strategy" | "portfolio";

const TABS: { key: Tab; label: string }[] = [
  { key: "chat", label: "💬 聊天" },
  { key: "strategy", label: "📋 策略描述" },
  { key: "portfolio", label: "📈 持仓" },
];

export default function StrategyPage() {
  const { sid = "" } = useParams();
  const [portfolioKey, setPortfolioKey] = useState(0);
  const [docKey, setDocKey] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="strategy-page">
      <div className="tab-bar">
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
          />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "strategy" ? " visible" : ""}`}>
          <StrategyDocSidebar sid={sid} refreshKey={docKey} />
        </div>
        <div className={`tab-pane scroll-pane${activeTab === "portfolio" ? " visible" : ""}`}>
          <PortfolioSidebar sid={sid} refreshKey={portfolioKey} />
        </div>
      </div>
    </div>
  );
}
