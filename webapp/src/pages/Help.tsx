import { CircleHelp } from "lucide-react";

export default function Help() {
  return (
    <div data-testid="help-page">
      <div className="rounded-2xl bg-gradient-to-br from-fleet-800 to-fleet-900 border border-fleet-700 p-6 mb-6">
        <div className="flex items-center gap-3 mb-1">
          <CircleHelp className="h-6 w-6 text-amber-400" />
          <h1 className="text-2xl font-bold text-white">Help</h1>
        </div>
        <p className="text-base text-fleet-200">
          Fleet Pulse watches repos, builds, sessions, ports, and backend liveness. It never restarts anything.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <HelpCard title="What each tab means">
          <HelpRow k="Fleet Status" v="Git activity (48h) + dirty repos. Click a repo for branch, commit, build log, changelog." />
          <HelpRow k="Backend Health" v="Per-repo TCP + listener PID + read-only service state + HTTP HealthPath probe. Verdicts: healthy, degraded, dead, listening-but-hung, unbound, conflict." />
          <HelpRow k="Builds" v="Recent BUILD_LOG.md entries across the fleet, newest first." />
          <HelpRow k="Sessions" v="Agent session docs from the last 72h." />
          <HelpRow k="Port Map" v="TCP liveness vs WEBAPP_PORTS.md registry. Ownership detail lives in Backend Health." />
          <HelpRow k="Tools" v="Live MCP tool surface from this backend." />
        </HelpCard>

        <HelpCard title="Ports and endpoints">
          <HelpRow k="Backend" v="10918 (REST + MCP HTTP). Endpoints: /health, /status, /activity, /dirty, /builds, /sessions, /portmap, /backend-health, /tools, /deps, /repo, /buildlog, /changelog." />
          <HelpRow k="Frontend" v="10919 (Vite dev). Proxies /api/* to the backend." />
          <HelpRow k="Registry" v="mcp-central-docs/operations/WEBAPP_PORTS.md is the source of truth for expected ports." />
        </HelpCard>

        <HelpCard title="NSSM restarts (hard rule)">
          <p className="text-base text-fleet-100 leading-relaxed">
            Restart with the service manager, never by killing the child:{" "}
            <code className="text-amber-300">sc.exe stop &lt;svc&gt;</code> +{" "}
            <code className="text-amber-300">sc.exe start &lt;svc&gt;</code>, then verify a NEW PID owns the
            port. Fleet Pulse suggests the command (copy button); execution happens in an admin shell or via
            windows-operations-mcp winops_svc. See TRAPS_AND_PITFALLS #22.
          </p>
        </HelpCard>

        <HelpCard title="Scope notes (PRD)">
          <HelpRow k="No Chat / Skills / LLM" v="Internal observer with no inference of its own; local-LLM chat is out of scope by design." />
          <HelpRow k="No actuation" v="No start/stop/restart tools. Companion: windows-operations-mcp winops_svc for SCM actuation." />
          <HelpRow k="Logs" v="Use the Logs overlay (topbar) for this session's API call history; backend ring log is a follow-up." />
        </HelpCard>
      </div>
    </div>
  );
}

function HelpCard({ title, children }: { title: string; children: any }) {
  return (
    <section className="bg-fleet-800/60 rounded-xl p-5 border border-fleet-700">
      <h2 className="text-lg font-semibold text-white mb-3">{title}</h2>
      <div className="space-y-2.5">{children}</div>
    </section>
  );
}

function HelpRow({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <p className="text-base font-medium text-amber-300">{k}</p>
      <p className="text-base text-fleet-100 leading-relaxed">{v}</p>
    </div>
  );
}
