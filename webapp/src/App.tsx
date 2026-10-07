import { useState, useEffect, useCallback } from "react";
import { Activity, Package, FileText, Map, Server, RefreshCw, HeartPulse, Wrench, CircleHelp, Terminal } from "lucide-react";
import FleetStatus from "./pages/FleetStatus";
import BackendHealth from "./pages/BackendHealth";
import Builds from "./pages/Builds";
import Sessions from "./pages/Sessions";
import PortMap from "./pages/PortMap";
import ToolsPage from "./pages/ToolsPage";
import Help from "./pages/Help";
import { fetchBackendHealth } from "./api";

type Tab = "status" | "health" | "builds" | "sessions" | "ports" | "tools" | "help";

const TABS: { id: Tab; label: string; icon: typeof Activity }[] = [
  { id: "status", label: "Fleet Status", icon: Server },
  { id: "health", label: "Backend Health", icon: HeartPulse },
  { id: "builds", label: "Builds", icon: Package },
  { id: "sessions", label: "Sessions", icon: FileText },
  { id: "ports", label: "Port Map", icon: Map },
  { id: "tools", label: "Tools", icon: Wrench },
  { id: "help", label: "Help", icon: CircleHelp },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("status");
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const h = await fetchBackendHealth();
      setBackendOk(h.status === "ok");
    } catch {
      setBackendOk(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <div className="min-h-screen bg-fleet-900" data-testid="fleet-pulse">
      {/* Topbar */}
      <header className="border-b border-fleet-700 bg-fleet-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-amber-400" />
          <h1 className="text-lg font-semibold text-white">Fleet Pulse</h1>
          <span
            data-testid="backend-dot"
            className={`w-2 h-2 rounded-full ${
              backendOk === null ? "bg-fleet-500" : backendOk ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-xs text-fleet-400">
            {backendOk === null ? "connecting..." : backendOk ? "connected" : "offline"}
          </span>
        </div>
        <button
          onClick={checkHealth}
          className="p-1.5 rounded hover:bg-fleet-700 text-fleet-400 hover:text-white"
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </header>

      {/* Tabs */}
      <nav className="border-b border-fleet-700 px-6 flex gap-1" data-testid="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            data-testid={`tab-${t.id}`}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors ${
              tab === t.id
                ? "border-amber-400 text-amber-400"
                : "border-transparent text-fleet-400 hover:text-fleet-200"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="p-6 max-w-6xl mx-auto" data-testid="page-content">
        {tab === "status" && <FleetStatus />}
        {tab === "health" && <BackendHealth />}
        {tab === "builds" && <Builds />}
        {tab === "sessions" && <Sessions />}
        {tab === "ports" && <PortMap />}
        {tab === "tools" && <ToolsPage />}
        {tab === "help" && <Help />}
      </main>
    </div>
  );
}
