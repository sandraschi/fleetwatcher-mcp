import { useState, useEffect } from "react";
import { fetchBuilds } from "../api";
import RepoModal from "../components/RepoModal";

export default function Builds() {
  const [builds, setBuilds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetchBuilds(30)
      .then((d) => setBuilds(d.builds || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-fleet-400 text-sm">Loading builds...</p>;
  if (error) return <p className="text-red-400 text-sm">{error}</p>;

  return (
    <div data-testid="builds-page">
      <div className="grid gap-3">
        {builds.length === 0 && <p className="text-fleet-500 text-sm">No BUILD_LOG.md entries found across the fleet</p>}
        {builds.map((b, i) => (
          <button
            key={i}
            onClick={() => setSelected(b.repo)}
            className="w-full text-left bg-fleet-800 rounded-xl p-5 border border-fleet-700 hover:bg-fleet-700 hover:border-fleet-600 transition-colors"
            data-testid={`build-${b.repo}`}
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-white font-medium">{b.repo || "unknown"}</span>
              <span className="text-fleet-400 text-xs">{b.timestamp || ""}</span>
            </div>
            {b.status && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                b.status === "pass" || b.status === "success"
                  ? "bg-green-900/50 text-green-400"
                  : "bg-red-900/50 text-red-400"
              }`}>
                {b.status}
              </span>
            )}
            {b.size && <span className="text-fleet-400 text-xs ml-2">{b.size}</span>}
            {b.duration && <span className="text-fleet-400 text-xs ml-2">{b.duration}</span>}
          </button>
        ))}
      </div>

      {selected && <RepoModal repo={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
