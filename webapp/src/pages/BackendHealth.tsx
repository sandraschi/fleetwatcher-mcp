import { useState, useEffect, useMemo } from "react";
import { HeartPulse, Copy, Check } from "lucide-react";
import { fetchBackendHealthDetail } from "../api";

type Verdict =
  | "healthy"
  | "degraded"
  | "dead"
  | "listening-but-hung"
  | "unbound"
  | "conflict"
  | "unknown-listening";

const VERDICT_STYLE: Record<Verdict, string> = {
  healthy: "bg-green-900/50 text-green-300",
  degraded: "bg-amber-900/50 text-amber-300",
  dead: "bg-red-900/50 text-red-300",
  "listening-but-hung": "bg-red-900/50 text-red-300",
  unbound: "bg-fleet-700 text-fleet-200",
  conflict: "bg-red-900/50 text-red-300",
  "unknown-listening": "bg-fleet-700 text-fleet-200",
};

export default function BackendHealth() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    fetchBackendHealthDetail()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const backends = useMemo(() => (data?.backends || []) as any[], [data]);
  const summary = useMemo(() => (data?.summary || {}) as Record<string, number>, [data]);
  const visible = useMemo(
    () => (filter === "all" ? backends : backends.filter((b) => b.verdict === filter)),
    [backends, filter],
  );

  if (loading) return <p className="text-base text-fleet-200">Probing backends...</p>;
  if (error) return <p className="text-base text-red-300">{error}</p>;
  if (!data) return null;

  const copyRemediation = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  const verdicts = Object.keys(summary).sort();

  return (
    <div data-testid="backend-health">
      <div className="rounded-2xl bg-gradient-to-br from-fleet-800 to-fleet-900 border border-fleet-700 p-6 mb-6" data-testid="hero">
        <div className="flex items-center gap-3 mb-1">
          <HeartPulse className="h-6 w-6 text-amber-400" />
          <h1 className="text-2xl font-bold text-white">Backend Health</h1>
        </div>
        <p className="text-base text-fleet-200 mb-5">
          Observer only: TCP + listener PID + read-only service state + HTTP probe. Never restarts anything.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <HealthKpi label="backends tracked" value={String(data.count ?? backends.length)} />
          <HealthKpi label="healthy" value={String(summary.healthy ?? 0)} accent="text-green-300" />
          <HealthKpi
            label="dead"
            value={String(summary.dead ?? 0)}
            accent={(summary.dead ?? 0) > 0 ? "text-red-300" : "text-white"}
          />
          <HealthKpi
            label="hung / degraded"
            value={String((summary["listening-but-hung"] ?? 0) + (summary.degraded ?? 0))}
            accent="text-amber-300"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4" data-testid="verdict-filter">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")} label={`all (${backends.length})`} />
        {verdicts.map((v) => (
          <FilterButton key={v} active={filter === v} onClick={() => setFilter(v)} label={`${v} (${summary[v]})`} />
        ))}
      </div>

      <div className="space-y-2">
        {visible.map((b: any) => (
          <div
            key={`${b.port}-${b.repo}`}
            className="bg-fleet-800/60 rounded-xl px-4 py-3 border border-fleet-700"
            data-testid={`health-${b.repo}`}
          >
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-amber-300 font-mono text-base w-16">{b.port}</span>
              <span className="text-white text-base font-medium flex-1 min-w-[10rem]">{b.repo}</span>
              <span className={`text-sm px-2.5 py-1 rounded ${VERDICT_STYLE[b.verdict as Verdict] ?? "bg-fleet-700 text-fleet-200"}`}>
                {b.verdict}
              </span>
            </div>
            <div className="mt-1.5 text-sm text-fleet-200 flex flex-wrap gap-x-4 gap-y-1">
              <span>PID: {b.pid ?? "unknown"}</span>
              <span>service: {b.service ? `${b.service} (${b.service_state})` : "not installed / unknown"}</span>
              {b.http && <span>HTTP {b.http.status ?? "no response"} · {b.http.ms}ms</span>}
            </div>
            {b.remediation && (
              <button
                onClick={() => copyRemediation(b.repo, b.remediation)}
                className="mt-2 inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded bg-fleet-700 border border-fleet-600 text-fleet-100 hover:bg-fleet-600"
                data-testid={`remediation-${b.repo}`}
                title="Copy NSSM-safe restart command (read-only suggestion, does not execute)"
              >
                {copied === b.repo ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied === b.repo ? "copied" : "copy restart command"}
              </button>
            )}
          </div>
        ))}
        {visible.length === 0 && <p className="text-base text-fleet-200">No backends match this filter.</p>}
      </div>
    </div>
  );
}

function HealthKpi({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-black/30 border border-fleet-700 rounded-xl p-4">
      <div className={`text-3xl font-bold ${accent || "text-white"}`}>{value}</div>
      <div className="text-fleet-200 text-sm mt-1">{label}</div>
    </div>
  );
}

function FilterButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
        active ? "bg-amber-400/15 border-amber-400 text-amber-300" : "bg-fleet-800 border-fleet-700 text-fleet-200 hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}
