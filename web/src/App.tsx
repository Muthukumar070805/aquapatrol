import { Routes, Route, NavLink } from "react-router-dom";
import ConsoleStrip from "./components/ConsoleStrip";
import Overview from "./pages/Overview";
import QuickDetect from "./pages/QuickDetect";
import SceneMonitor from "./pages/SceneMonitor";
import Hindcast from "./pages/Hindcast";
import Vessels from "./pages/Vessels";
import CaseDetail from "./pages/CaseDetail";
import Report from "./pages/Report";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/detect", label: "Quick Detect" },
  { to: "/scenes", label: "Scene Monitor" },
  { to: "/hindcast", label: "Hindcast" },
  { to: "/vessels", label: "Vessels" },
] as const;

export default function App() {
  return (
    <div className="app">
      <ConsoleStrip />
      <header className="topbar">
        <div className="brand">Satellite Oil Spill Forensics</div>
        <nav className="nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : undefined}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/detect" element={<QuickDetect />} />
          <Route path="/scenes" element={<SceneMonitor />} />
          <Route path="/hindcast" element={<Hindcast />} />
          <Route path="/vessels" element={<Vessels />} />
          <Route path="/cases/:id" element={<CaseDetail />} />
          <Route path="/reports/:id" element={<Report />} />
        </Routes>
      </main>
    </div>
  );
}
