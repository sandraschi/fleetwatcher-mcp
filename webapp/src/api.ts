// Fleet Pulse webapp talks to the backend REST facade (plain JSON) through the
// Vite /api proxy. No MCP session or SSE involved.
const API = "/api";

async function get(path: string): Promise<any> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`HTTP ${r.status} on ${path}`);
  const data = await r.json();
  if (data && data.success === false) throw new Error(data.error || "Request failed");
  return data;
}

export async function fetchFleetStatus() {
  return get("/dirty");
}

export async function fetchRecentActivity(hours = 24) {
  return get(`/activity?hours=${hours}`);
}

export async function fetchBuilds(limit = 20) {
  return get(`/builds?limit=${limit}`);
}

export async function fetchSessions(hours = 48) {
  return get(`/sessions?hours=${hours}`);
}

export async function fetchPortMap() {
  return get("/portmap");
}

export async function fetchServerDeps() {
  return get("/deps");
}

export async function fetchRepoStatus(name: string) {
  return get(`/repo?name=${encodeURIComponent(name)}`);
}

export async function fetchBuildLog(name: string) {
  return get(`/buildlog?name=${encodeURIComponent(name)}`);
}

export async function fetchChangelog(name: string) {
  return get(`/changelog?name=${encodeURIComponent(name)}`);
}

export async function fetchBackendHealth() {
  return get("/health");
}

export async function fetchBackendHealthDetail() {
  return get("/backend-health");
}

export async function fetchTools() {
  return get("/tools");
}
