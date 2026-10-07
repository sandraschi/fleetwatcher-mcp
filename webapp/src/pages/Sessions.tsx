import { useState, useEffect } from "react";
import { fetchSessions } from "../api";

export default function Sessions() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSessions(72)
      .then((d) => setSessions(d.sessions || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-fleet-400 text-sm">Loading sessions...</p>;
  if (error) return <p className="text-red-400 text-sm">{error}</p>;

  return (
    <div data-testid="sessions-page">
      <div className="grid gap-3">
        {sessions.length === 0 && <p className="text-fleet-500 text-sm">No session docs from the last 72 hours</p>}
        {sessions.map((s, i) => (
          <div key={i} className="bg-fleet-800 rounded-xl p-5 border border-fleet-700">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-white font-medium">{s.title || "Untitled"}</p>
                <p className="text-fleet-400 text-xs mt-1">{s.path}</p>
              </div>
              <div className="text-right text-fleet-400 text-xs">
                <div>{s.size ? `${(s.size / 1024).toFixed(1)} KB` : ""}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
