import { useState, useEffect } from "react";
import {
  X, GitBranch, FileText, Hammer, Wrench, AlertTriangle, Activity, Cloud,
  ExternalLink, GitCommit, Calendar, ListTree,
} from "lucide-react";
import { fetchRepoStatus, fetchBuildLog, fetchChangelog } from "../api";

export default function RepoModal({ repo, onClose }: { repo: string; onClose: () => void }) {
  const [status, setStatus] = useState<any>(null);
  const [buildLog, setBuildLog] = useState<string | null>(null);
  const [changelog, setChangelog] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRepoStatus(repo)
      .then((d) => setStatus(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [repo]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const load = (key: "buildLog" | "changelog", fn: () => Promise<any>) => {
    const current = key === "buildLog" ? buildLog : changelog;
    if (current !== null) {
      if (key === "buildLog") setBuildLog(null); else setChangelog(null);
      return;
    }
    fn().then((d) => {
      const text = d.content || "(empty)";
      if (key === "buildLog") setBuildLog(text); else setChangelog(text);
    }).catch((e) => {
      const msg = `Failed to load: ${e.message}`;
      if (key === "buildLog") setBuildLog(msg); else setChangelog(msg);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-6 bg-black/60 overflow-y-auto" onClick={onClose} data-testid="repo-modal">
      <div className="bg-fleet-900 border border-fleet-700 rounded-xl w-full max-w-2xl shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-fleet-700">
          <div className="flex items-center gap-3 min-w-0">
            <h2 className="text-lg font-semibold text-white font-mono truncate">{repo}</h2>
            {status?.github_url && (
              <a
                href={status.github_url}
                target="_blank"
                rel="noreferrer"
                className="text-fleet-400 hover:text-white inline-flex items-center gap-1 text-sm"
                data-testid="github-link"
              >
                <ExternalLink className="h-4 w-4" /> GitHub
              </a>
            )}
          </div>
          <button onClick={onClose} className="text-fleet-400 hover:text-white" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5">
          {loading && <p className="text-fleet-400">Loading repo status...</p>}
          {error && <p className="text-red-400">{error}</p>}

          {status && (
            <>
              {status.description && (
                <p className="text-fleet-200 mb-4 leading-relaxed" data-testid="repo-description">
                  {status.description}
                </p>
              )}

              <div className="grid grid-cols-3 gap-3 mb-5">
                <Stat icon={<GitBranch className="h-4 w-4" />} label="branch" value={status.branch || "unknown"} />
                <Stat icon={<GitCommit className="h-4 w-4" />} label="commits" value={status.commit_count != null ? String(status.commit_count) : "—"} />
                <Stat icon={<Activity className="h-4 w-4" />} label="dirty" value={status.dirty ? "yes" : "no"} />
                <Stat icon={<Calendar className="h-4 w-4" />} label="last commit" value={status.last_commit_iso || "—"} />
                <Stat icon={<Cloud className="h-4 w-4" />} label="remote" value={status.has_remote ? "yes" : "no"} />
                <Stat icon={<Hammer className="h-4 w-4" />} label="tauri" value={status.has_tauri ? "yes" : "no"} />
              </div>

              {status.last_commit_msg && (
                <div className="mb-4">
                  <p className="text-fleet-400 text-xs uppercase tracking-wider mb-1">last commit</p>
                  <p className="text-white break-words">{status.last_commit_msg}</p>
                  {status.last_commit_hash && (
                    <p className="text-fleet-400 text-xs font-mono mt-1">{status.last_commit_hash.slice(0, 12)}</p>
                  )}
                </div>
              )}

              <div className="flex gap-2 mb-4">
                {status.has_nopublish && <Badge className="bg-red-900/50 text-red-400">nopublish</Badge>}
                {status.has_ai_readiness && <Badge className="bg-amber-900/50 text-amber-400">ai-readiness</Badge>}
                {status.has_assfix_timestamp && <Badge className="bg-fleet-700 text-fleet-300">assfix</Badge>}
              </div>

              <div className="flex gap-2 flex-wrap">
                {status.has_build_log && (
                  <button
                    onClick={() => load("buildLog", () => fetchBuildLog(repo))}
                    className="px-3 py-1.5 text-sm rounded bg-fleet-800 border border-fleet-600 text-white hover:bg-fleet-700"
                    data-testid="build-log-toggle"
                  >
                    {buildLog === null ? "Show build log" : "Hide build log"}
                  </button>
                )}
                {status.has_changelog && (
                  <button
                    onClick={() => load("changelog", () => fetchChangelog(repo))}
                    className="px-3 py-1.5 text-sm rounded bg-fleet-800 border border-fleet-600 text-white hover:bg-fleet-700"
                    data-testid="changelog-toggle"
                  >
                    {changelog === null ? "Show changelog" : "Hide changelog"}
                  </button>
                )}
              </div>

              {buildLog !== null && (
                <DocBlock title="Build log" text={buildLog} />
              )}
              {changelog !== null && (
                <DocBlock title="Changelog" text={changelog} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="bg-fleet-800 rounded-lg px-3 py-2.5 border border-fleet-700 flex items-center gap-2">
      <span className="text-fleet-300 shrink-0">{icon}</span>
      <div className="min-w-0">
        <div className="text-fleet-200 text-xs uppercase tracking-wider">{label}</div>
        <div className="text-white text-base truncate">{value}</div>
      </div>
    </div>
  );
}

function DocBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="mt-4">
      <p className="text-fleet-400 text-xs uppercase tracking-wider mb-1 flex items-center gap-1">
        <ListTree className="h-3.5 w-3.5" /> {title}
      </p>
      <pre className="max-h-80 overflow-y-auto bg-black/40 border border-fleet-700 rounded-lg p-3 text-xs text-fleet-200 whitespace-pre-wrap">
        {text}
      </pre>
    </div>
  );
}

function Badge({ children, className }: { children: any; className?: string }) {
  return <span className={`text-xs px-2 py-0.5 rounded ${className || ""}`}>{children}</span>;
}
