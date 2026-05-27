import { Link, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import StrategyPage from "./pages/StrategyPage";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">aistock</Link>
        <span className="tagline">Claude Code 自主交易控制台</span>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/s/:sid" element={<StrategyPage />} />
        </Routes>
      </main>
    </div>
  );
}
