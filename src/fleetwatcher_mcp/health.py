"""Backend health observer - read-only fleet watchdog.

Observer, NOT actuator. This module never starts, stops, or restarts
anything. Actuation stays in windows-operations-mcp (winops_svc/*) or
manual ``sc.exe``. fleetwatcher reports + suggests remediation strings.

For each repo with a ``fleet-start.config.ps1`` we join:
  WEBAPP_PORTS.md registry -> expected repo per port
  fleet-start.config.ps1   -> BackendPort + HealthPath per repo
  TCP connect              -> listening or not (fast, 0.2s)
  listener PID             -> Get-NetTCPConnection owner (best effort)
  SCM query (read-only)    -> service state for name candidates
  HTTP GET HealthPath      -> 200 or hung (2s timeout)

Verdicts: healthy | degraded | dead | listening-but-hung | unbound
         | conflict | unknown-listening
"""

from __future__ import annotations

import concurrent.futures as _fut
import logging
import os
import re
import socket
import subprocess
import time

logger = logging.getLogger("fleetwatcher.health")

_BACKEND_PORT_RE = re.compile(r"BackendPort\s*=\s*(\d{4,5})")
_HEALTH_PATH_RE = re.compile(r"HealthPath\s*=\s*['\"]([^'\"]+)['\"]")
_NAME_RE = re.compile(r"Name\s*=\s*['\"]([^'\"]+)['\"]")

_DEFAULT_HEALTH_PATHS = ("/api/health", "/health", "/api/status", "/status")

_SERVICE_CANDIDATE_SUFFIXES = ("", "-mcp", "-backend", "-svc")


def parse_fleet_config(repo_path: str) -> dict:
    """Parse BackendPort/HealthPath/Name from fleet-start.config.ps1.

    Pure regex read, never executes PowerShell. Returns {} when absent.
    """
    cfg = os.path.join(repo_path, "fleet-start.config.ps1")
    out: dict = {}
    try:
        with open(cfg, encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return out
    m = _BACKEND_PORT_RE.search(text)
    if m:
        try:
            out["backend_port"] = int(m.group(1))
        except ValueError:
            pass
    h = _HEALTH_PATH_RE.search(text)
    if h:
        out["health_path"] = h.group(1)
    n = _NAME_RE.search(text)
    if n:
        out["config_name"] = n.group(1)
    return out


def _tcp_open(port: int, timeout: float = 0.2) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def listener_pid(port: int, timeout: int = 8) -> int | None:
    """Best-effort owning PID of a listening TCP port.

    Uses Get-NetTCPConnection. Returns None on any failure (soft
    degradation, never raises). Read-only.
    """
    ps = (
        "Get-NetTCPConnection -LocalPort " + str(port) + " -State Listen -ErrorAction SilentlyContinue"
        " | Select-Object -First 1 -ExpandProperty OwningProcess"
    )
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        txt = (r.stdout or "").strip()
        return int(txt) if txt.isdigit() else None
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, OSError):
        return None


def service_state(candidate: str, timeout: int = 10) -> dict:
    """Read-only SCM query for one service name via sc.exe.

    Returns {"found": bool, "state": str}. Never mutates.
    """
    try:
        r = subprocess.run(
            ["sc.exe", "query", candidate],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("sc.exe query failed for %s: %s", candidate, exc_info=True)
        return {"found": False, "state": "unknown", "error": str(e)}
    out = r.stdout or ""
    if "FAILED 1060" in out or "specified service does not exist" in out.lower():
        return {"found": False, "state": "not-installed"}
    m = re.search(r"STATE\s*:\s*\d+\s+(\w+)", out)
    return {"found": True, "state": (m.group(1).lower() if m else "unknown")}


def service_candidates(repo: str) -> list[str]:
    """NSSM/SCM name candidates for a repo, most likely first."""
    seen: list[str] = []
    for suffix in _SERVICE_CANDIDATE_SUFFIXES:
        name = f"{repo}{suffix}"
        if name not in seen:
            seen.append(name)
    return seen


def http_probe(port: int, health_path: str, timeout: float = 2.0) -> dict:
    """GET http://127.0.0.1:port/health_path. Read-only, short timeout."""
    url = f"http://127.0.0.1:{port}{health_path}"
    start = time.time()
    try:
        import httpx

        r = httpx.get(url, timeout=timeout)
        ms = int((time.time() - start) * 1000)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "ms": ms, "url": url}
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        logger.debug("health probe failed %s: %s", url, e)
        return {"ok": False, "status": None, "ms": ms, "url": url, "error": str(e)[:160]}


def classify(
    *,
    listening: bool,
    http_ok: bool | None,
    http_status: int | None,
    expected: str | None,
    claimed_by: list[str],
) -> str:
    """Pure verdict classifier (unit-tested, no I/O).

    Args:
        listening: TCP connect succeeded.
        http_ok: probe success (None when probe skipped).
        http_status: HTTP status code or None.
        expected: registry-expected repo for this port.
        claimed_by: repos whose fleet-start claims this port.
    """
    if len(claimed_by) > 1:
        return "conflict"
    if not listening:
        return "dead" if expected else "unbound"
    if http_ok is True:
        return "healthy"
    if http_ok is False:
        return "listening-but-hung"
    if http_status is not None and http_status >= 500:
        return "degraded"
    return "unknown-listening"


def remediation(service: str | None, port: int) -> str:
    """NSSM-safe restart suggestion (string only, never executed)."""
    svc = service or "<service-name>"
    return (
        f"sc.exe stop {svc} && sc.exe start {svc} "
        f"-- then verify a NEW PID owns :{port} "
        f"(never taskkill the child; see TRAPS_AND_PITFALLS #22)"
    )


def _check_one(
    repo: str,
    port: int,
    health_path: str | None,
    expected: str | None,
    claimed_by: list[str],
    probe_http: bool = True,
) -> dict:
    listening = _tcp_open(port)
    pid = listener_pid(port) if listening else None
    http: dict | None = None
    if listening and probe_http:
        paths = [health_path] if health_path else list(_DEFAULT_HEALTH_PATHS)
        for p in paths:
            http = http_probe(port, p)
            if http["ok"]:
                break
    svc_info: dict = {"found": False, "state": "unknown", "checked": []}
    for cand in service_candidates(repo):
        st = service_state(cand)
        svc_info["checked"].append(cand)
        if st["found"]:
            svc_info = {**st, "service": cand, "checked": svc_info["checked"]}
            break
    verdict = classify(
        listening=listening,
        http_ok=(http["ok"] if http else None),
        http_status=(http["status"] if http else None),
        expected=expected,
        claimed_by=claimed_by,
    )
    return {
        "repo": repo,
        "port": port,
        "expected": expected,
        "health_path": health_path or "(default probe set)",
        "listening": listening,
        "pid": pid,
        "service": svc_info.get("service"),
        "service_state": svc_info.get("state", "unknown"),
        "http": http,
        "verdict": verdict,
        "remediation": remediation(svc_info.get("service"), port)
        if verdict in ("dead", "listening-but-hung", "degraded")
        else None,
    }


def backend_health(
    repos_root: str,
    registry_path: str,
    *,
    probe_http: bool = True,
    max_workers: int = 16,
    limit: int = 300,
) -> dict:
    """Check every repo backend: TCP + PID + SCM (read-only) + HTTP probe.

    Bounded: caps repos at `limit`, each probe has short timeouts,
    TCP+HTTP run in a thread pool. Never raises on per-repo failure;
    failures degrade that row to unknown with error detail.
    """
    from .graph import _parse_port_registry

    registered = _parse_port_registry(registry_path)
    claimed: dict[int, list[str]] = {}
    rows: list[tuple[str, int, str | None]] = []
    try:
        names = sorted(os.listdir(repos_root))[:limit]
    except OSError as e:
        logger.warning("repos root unreadable %s", repos_root, exc_info=True)
        return {"success": False, "error": str(e), "backends": [], "count": 0}
    for name in names:
        repo_path = os.path.join(repos_root, name)
        if not os.path.isdir(repo_path):
            continue
        cfg = parse_fleet_config(repo_path)
        port = cfg.get("backend_port")
        if not isinstance(port, int):
            continue
        rows.append((name, port, cfg.get("health_path")))
        claimed.setdefault(port, []).append(name)
    expected_of = {p: registered.get(p) for p in claimed}

    def _safe(row: tuple[str, int, str | None]) -> dict:
        repo, port, hpath = row
        try:
            return _check_one(repo, port, hpath, expected_of.get(port), claimed.get(port, [repo]), probe_http)
        except Exception as e:
            logger.warning("health check failed for %s:%s", repo, port, exc_info=True)
            return {
                "repo": repo,
                "port": port,
                "expected": expected_of.get(port),
                "listening": False,
                "pid": None,
                "verdict": "unknown-listening",
                "error": str(e)[:200],
                "remediation": None,
            }

    with _fut.ThreadPoolExecutor(max_workers=max_workers) as pool:
        backends = list(pool.map(_safe, rows))
    backends.sort(key=lambda b: (b["port"], b["repo"]))
    summary: dict[str, int] = {}
    for b in backends:
        summary[b["verdict"]] = summary.get(b["verdict"], 0) + 1
    return {
        "success": True,
        "backends": backends,
        "summary": summary,
        "count": len(backends),
    }
