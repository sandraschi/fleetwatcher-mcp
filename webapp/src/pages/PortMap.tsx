import { useState, useEffect } from "react";
import { fetchPortMap } from "../api";

export default function PortMap() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPortMap()
      .then((d) => setData(d.data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-fleet-400 text-sm">Scanning ports...</p>;
  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!data) return null;

  return (
    <div data-testid="port-map">
      {/* KPI summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-fleet-800 rounded-xl p-5 border border-fleet-700">
          <div className="text-2xl font-bold text-white">{data.registered_count}</div>
          <div className="text-fleet-400 text-sm">registered ports</div>
        </div>
        <div className="bg-fleet-800 rounded-xl p-5 border border-fleet-700">
          <div className="text-2xl font-bold text-white">{data.live_count}</div>
          <div className="text-fleet-400 text-sm">live services</div>
        </div>
        <div className="bg-fleet-800 rounded-xl p-5 border border-fleet-700">
          <div className={`text-2xl font-bold ${data.conflicts > 0 ? "text-red-400" : "text-green-400"}`}>
            {data.conflicts}
          </div>
          <div className="text-fleet-400 text-sm">conflicts</div>
        </div>
      </div>

      {/* Mapped ports — TCP liveness only. Ownership detail lives in Backend Health. */}
      <p className="text-sm text-fleet-200 mb-3">
        TCP liveness vs registry. Green means something is listening, not that the expected repo owns the
        port — see Backend Health for PID + probe verdicts.
      </p>
      <div className="space-y-1">
        {(data.mapped || []).map((m: any) => (
          <div key={m.port} className="flex items-center gap-4 px-4 py-2.5 text-sm bg-fleet-800/50 rounded-lg">
            <span className="text-amber-300 font-mono text-base w-16">{m.port}</span>
            <span className="text-white text-base flex-1">{m.expected}</span>
            <span className={`text-sm px-2.5 py-1 rounded ${
              m.conflict ? "bg-red-900/50 text-red-300" :
              m.actual ? "bg-green-900/50 text-green-300" :
              "bg-fleet-700 text-fleet-200"
            }`}>
              {m.conflict ? "conflict" : m.actual ? "live" : "idle"}
            </span>
          </div>
        ))}
      </div>

      {/* Unmapped */}
      {data.unmapped_ports && Object.keys(data.unmapped_ports).length > 0 && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">
            Unregistered Ports ({Object.keys(data.unmapped_ports).length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.unmapped_ports).map(([port, service]) => (
              <span key={port} className="text-xs bg-fleet-700 px-2 py-1 rounded text-fleet-300 font-mono">
                {port}: {String(service)}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
