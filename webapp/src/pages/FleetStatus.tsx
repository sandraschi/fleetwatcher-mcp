import { useState, useEffect } from "react";
import { GitBranch, AlertTriangle, Activity, Boxes, Layers } from "lucide-react";
import { fetchRecentActivity, fetchFleetStatus } from "../api";
import RepoModal from "../components/RepoModal";

export default function FleetStatus() {
  const [recent, setRecent] = useState<any[]>([]);
  const [dirty, setDirty] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [r, d] = await Promise.all([
          fetchRecentActivity(48),
          fetchFleetStatus(),
        ]);
        setRecent(r.repos || []);
        setDirty(d.repos || []);
        setUpdatedAt(new Date().toLocaleTimeString());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p className="text-fleet-400">Loading...</p>;
  if (error) return <p className="text-red-400">{error}</p>;

  const dirtyCount = dirty.length;
  const activeCount = recent.length;

  return (
    <div data-testid="fleet-status">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-fleet-800 to-fleet-900 border border-fleet-700 p-6 mb-8" data-testid="hero">
        <div className="flex items-center gap-3 mb-1">
          <Boxes className="h-6 w-6 text-amber-400" />
          <h1 className="text-2xl font-bold text-white">Fleet Overview</h1>
        </div>
        <p className="text-fleet-300 mb-5">Live pulse across every MCP server and webapp repo in the fleet.</p>

        <div className="grid grid-cols-3 gap-4">
          <HeroKpi label="repos tracked" value={String(recent.length || "—")} />
          <HeroKpi label="active (48h)" value={String(activeCount)} accent="text-amber-400" />
          <HeroKpi label="dirty" value={String(dirtyCount)} accent="text-red-400" />
        </div>

        {updatedAt && (
          <p className="text-fleet-400 text-xs mt-4">Updated {updatedAt}</p>
        )}
      </div>

      {/* Dirty repos */}
      {dirtyCount > 0 && (
        <section className="mb-8">
          <h2 className="text-base font-semibold text-amber-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Dirty Repos ({dirtyCount})
          </h2>
          <div className="space-y-2">
            {dirty.map((r: any) => (
              <button
                key={r.repo}
                onClick={() => setSelected(r.repo)}
                className="w-full bg-fleet-800 rounded-lg px-4 py-3 border border-fleet-700 hover:bg-fleet-700 hover:border-fleet-600 transition-colors text-left"
                data-testid={`dirty-${r.repo}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium">{r.repo}</span>
                  <span className="text-fleet-400">{r.changed_files} file(s) ›</span>
                </div>
                {r.description && <p className="text-fleet-400 text-sm truncate mt-0.5">{r.description}</p>}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Recent activity */}
      <section>
        <h2 className="text-base font-semibold text-fleet-200 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Recent Commits ({activeCount})
        </h2>
        <div className="space-y-1">
          {recent.map((r: any) => (
            <button
              key={r.repo}
              onClick={() => setSelected(r.repo)}
              className="flex flex-col gap-0.5 px-4 py-2.5 w-full text-left hover:bg-fleet-800/60 rounded-lg transition-colors"
              data-testid={`recent-${r.repo}`}
            >
              <span className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-fleet-500 shrink-0" />
                <span className="text-white font-medium">{r.repo}</span>
                <span className="text-fleet-400 truncate flex-1">{r.last_commit_msg || r.last_assfix_ts || ""}</span>
                {r.has_nopublish && <span className="text-xs text-red-400">nopublish</span>}
                {r.has_ai_readiness && <span className="text-xs text-amber-400">ai-readiness</span>}
              </span>
              {r.description && <span className="text-fleet-400 text-sm truncate pl-6">{r.description}</span>}
            </button>
          ))}
          {recent.length === 0 && <p className="text-fleet-400">No activity in the last 48 hours</p>}
        </div>
      </section>

      {selected && <RepoModal repo={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function HeroKpi({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-black/30 border border-fleet-700 rounded-xl p-4">
      <div className={`text-3xl font-bold ${accent || "text-white"}`}>{value}</div>
      <div className="text-fleet-400 text-sm flex items-center gap-1">
        <Layers className="h-3.5 w-3.5" /> {label}
      </div>
    </div>
  );
}
