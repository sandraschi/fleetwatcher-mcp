import { useState, useEffect } from "react";
import { Wrench } from "lucide-react";
import { fetchTools } from "../api";

export default function ToolsPage() {
  const [tools, setTools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTools()
      .then((d) => setTools(d.tools || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-base text-fleet-200">Loading tools...</p>;
  if (error) return <p className="text-base text-red-300">{error}</p>;

  return (
    <div data-testid="tools-page">
      <div className="rounded-2xl bg-gradient-to-br from-fleet-800 to-fleet-900 border border-fleet-700 p-6 mb-6">
        <div className="flex items-center gap-3 mb-1">
          <Wrench className="h-6 w-6 text-amber-400" />
          <h1 className="text-2xl font-bold text-white">Tools</h1>
        </div>
        <p className="text-base text-fleet-200">
          Live tool surface from this backend (no hardcoded lists). Portmanteau operations are listed in each
          tool description.
        </p>
      </div>
      <div className="space-y-2">
        {tools.map((t) => (
          <div key={t.name} className="bg-fleet-800/60 rounded-xl px-4 py-3 border border-fleet-700" data-testid={`tool-${t.name}`}>
            <p className="text-white text-base font-mono">{t.name}</p>
            {t.description && <p className="text-fleet-200 text-sm mt-1">{t.description}</p>}
          </div>
        ))}
        {tools.length === 0 && <p className="text-base text-fleet-200">No tools reported by backend.</p>}
      </div>
    </div>
  );
}
