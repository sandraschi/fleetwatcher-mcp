"""fleetwatcher-mcp: Internal fleet pulse server."""

import logging
import os

from fastmcp import FastMCP

from . import builds, graph, health, pulse, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fleetwatcher")

mcp = FastMCP("fleetwatcher-mcp")

_REPOS_ROOT = os.environ.get("FLEETWATCHER_REPOS_ROOT", r"D:\Dev\repos")
_SESSIONS_ROOT = os.environ.get("FLEETWATCHER_SESSIONS_ROOT", r"D:\Dev\repos\mcp-agent-session-summaries\data\sessions")
_PORT_REGISTRY = os.environ.get(
    "FLEETWATCHER_PORT_REGISTRY", r"D:\Dev\repos\mcp-central-docs\operations\WEBAPP_PORTS.md"
)


# -- Pulse tools --


@mcp.tool()
async def fleet_pulse(operation: str, repo_path: str | None = None, hours: int = 24) -> dict:
    """Monitor fleet repo activity.

    Operations:
    - recent: repos with commits/assfix changes in the last N hours
    - repo: detailed status for one repo
    - dirty: repos with uncommitted changes

    ## Return Format
    {"success": bool, "repos": [...], "count": int}
    """
    if operation == "recent":
        return pulse.recent_activity(_REPOS_ROOT, hours)
    elif operation == "repo":
        if not repo_path:
            return {"success": False, "error": "repo_path required for 'repo' operation"}
        return pulse.repo_status(os.path.join(_REPOS_ROOT, repo_path))
    elif operation == "dirty":
        return pulse.dirty_repos(_REPOS_ROOT)
    return {"success": False, "error": f"Unknown operation: {operation}"}


@mcp.tool()
async def build_watch(operation: str, repo_name: str | None = None, limit: int = 20) -> dict:
    """Monitor NSIS builds and CI outcomes across the fleet.

    Operations:
    - recent: last N build attempts across all repos (from BUILD_LOG.md)
    - log: full BUILD_LOG.md content for one repo

    ## Return Format
    {"success": bool, "builds": [...], "count": int}
    """
    if operation == "recent":
        return builds.recent_builds(_REPOS_ROOT, limit)
    elif operation == "log":
        if not repo_name:
            return {"success": False, "error": "repo_name required for 'log' operation"}
        return builds.build_log(_REPOS_ROOT, repo_name)
    return {"success": False, "error": f"Unknown operation: {operation}"}


@mcp.tool()
async def session_scan(operation: str, query: str | None = None, hours: int = 48) -> dict:
    """Search and browse agent session documentation.

    Operations:
    - recent: session docs from the last N hours
    - search: full-text search across session doc content

    ## Return Format
    {"success": bool, "sessions": [...], "count": int}
    """
    if operation == "recent":
        return sessions.recent_sessions(_SESSIONS_ROOT, hours)
    elif operation == "search":
        if not query:
            return {"success": False, "error": "query required for 'search' operation"}
        return sessions.search_sessions(_SESSIONS_ROOT, query)
    return {"success": False, "error": f"Unknown operation: {operation}"}


@mcp.tool()
async def fleet_graph(operation: str) -> dict:
    """Fleet topology and dependency mapping.

    Operations:
    - dependencies: which MCP servers reference which other MCP servers
    - port_map: live port scan vs registered port assignments
    - health: backend liveness per repo (TCP + listener PID + read-only
      SCM state + HTTP HealthPath probe). Observer only, never restarts.

    ## Return Format
    {"success": bool, "data": any}
    """
    if operation == "dependencies":
        return graph.server_dependencies(_REPOS_ROOT)
    elif operation == "port_map":
        return graph.port_map(_REPOS_ROOT, _PORT_REGISTRY)
    elif operation == "health":
        return health.backend_health(_REPOS_ROOT, _PORT_REGISTRY)
    return {"success": False, "error": f"Unknown operation: {operation}"}


@mcp.tool()
def fleetwatcher_help() -> dict:
    """Show all fleetwatcher tools and usage."""
    return {
        "success": True,
        "message": (
            "fleetwatcher-mcp - internal fleet pulse\n\n"
            "fleet_pulse(operation, repo_path?, hours?) - repo activity\n"
            "  recent: repos changed in last N hours\n"
            "  repo: status for one repo\n"
            "  dirty: uncommitted changes\n\n"
            "build_watch(operation, repo_name?, limit?) - NSIS builds\n"
            "  recent: last N builds across fleet\n"
            "  log: BUILD_LOG.md for a repo\n\n"
            "session_scan(operation, query?, hours?) - session docs\n"
            "  recent: docs from last N hours\n"
            "  search: full-text search\n\n"
            "fleet_graph(operation) - topology + backend liveness\n"
            "  dependencies: MCP inter-server references\n"
            "  port_map: live vs registered ports\n"
            "  health: per-repo TCP + PID + read-only SCM + HTTP probe (observer only)\n\n"
            "fleetwatcher_help() - this message"
        ),
    }


@mcp.tool(annotations={"readonly": True})
def fleetwatcher_status() -> dict:
    """Health check and configuration summary."""
    return {
        "success": True,
        "status": "ok",
        "server": "fleetwatcher-mcp",
        "version": "0.1.0",
        "repos_root": _REPOS_ROOT,
        "sessions_root": _SESSIONS_ROOT,
        "port_registry": _PORT_REGISTRY,
    }


def main():
    import sys

    argv = sys.argv[1:]
    port = (
        os.environ.get("FLEETWATCHER_PORT")
        or os.environ.get("PORT")
        or os.environ.get("WEB_PORT")
    )
    if "--port" in argv:
        try:
            port = argv[argv.index("--port") + 1]
        except IndexError:
            pass
    for a in argv:
        if a.startswith("--port="):
            port = a.split("=", 1)[1]
    if not port and "--serve" in argv:
        port = "10918"  # registry default for fleetwatcher-mcp backend
    if port:
        import uvicorn
        from starlette.concurrency import run_in_threadpool
        from starlette.middleware.cors import CORSMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        host = os.environ.get("FLEETWATCHER_HOST", "127.0.0.1")
        app = mcp.http_app()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        )

        # -- REST facade (plain JSON for the webapp; no MCP session/SSE needed) --

        def q(request: Request, name: str, default: int) -> int:
            try:
                return int(request.query_params.get(name, default))
            except ValueError:
                return default

        def safe_name(raw: str | None) -> str | None:
            """Return a bare repo name, or None if it's a path-traversal attempt."""
            if not raw:
                return None
            name = raw.strip().strip("\\/")
            if not name or any(part in name for part in ("..", "\\", "/", ":")):
                return None
            return name

        async def health(request):
            return JSONResponse({"status": "ok", "server": "fleetwatcher-mcp", "version": "0.1.0"})

        async def status(request):
            return JSONResponse(
                {
                    "success": True,
                    "status": "ok",
                    "server": "fleetwatcher-mcp",
                    "version": "0.1.0",
                    "repos_root": _REPOS_ROOT,
                    "sessions_root": _SESSIONS_ROOT,
                    "port_registry": _PORT_REGISTRY,
                }
            )

        async def activity(request):
            return JSONResponse(await run_in_threadpool(pulse.recent_activity, _REPOS_ROOT, q(request, "hours", 24)))

        async def dirty(request):
            return JSONResponse(await run_in_threadpool(pulse.dirty_repos, _REPOS_ROOT))

        async def builds_endpoint(request):
            return JSONResponse(await run_in_threadpool(builds.recent_builds, _REPOS_ROOT, q(request, "limit", 20)))

        async def sessions_endpoint(request):
            return JSONResponse(
                await run_in_threadpool(sessions.recent_sessions, _SESSIONS_ROOT, q(request, "hours", 48))
            )

        async def portmap(request):
            return JSONResponse(await run_in_threadpool(graph.port_map, _REPOS_ROOT, _PORT_REGISTRY))

        async def backend_health(request):
            return JSONResponse(await run_in_threadpool(health.backend_health, _REPOS_ROOT, _PORT_REGISTRY))

        async def tools(request):
            try:
                tools_map = {t.name: t for t in await mcp.list_tools()}
                items = [
                    {"name": name, "description": (getattr(t, "description", "") or "")[:280]}
                    for name, t in tools_map.items()
                ]
            except Exception as e:
                logger.warning("tools listing failed", exc_info=True)
                items = []
                return JSONResponse({"success": False, "error": str(e)[:200], "tools": []})
            return JSONResponse({"success": True, "tools": sorted(items, key=lambda t: t["name"])})

        async def deps(request):
            return JSONResponse(await run_in_threadpool(graph.server_dependencies, _REPOS_ROOT))

        async def repo(request):
            name = safe_name(request.query_params.get("name"))
            if not name:
                return JSONResponse({"success": False, "error": "name query param required"}, status_code=400)
            repo_path = os.path.join(_REPOS_ROOT, name)
            if not os.path.isdir(repo_path):
                return JSONResponse({"success": False, "error": f"repo not found: {name}"}, status_code=404)
            return JSONResponse(await run_in_threadpool(pulse.repo_status, repo_path))

        async def buildlog(request):
            name = safe_name(request.query_params.get("name"))
            if not name:
                return JSONResponse({"success": False, "error": "name query param required"}, status_code=400)
            repo_path = os.path.join(_REPOS_ROOT, name)
            if not os.path.isdir(repo_path):
                return JSONResponse({"success": False, "error": f"repo not found: {name}"}, status_code=404)
            return JSONResponse(await run_in_threadpool(builds.build_log, _REPOS_ROOT, name))

        async def changelog(request):
            name = safe_name(request.query_params.get("name"))
            if not name:
                return JSONResponse({"success": False, "error": "name query param required"}, status_code=400)
            repo_path = os.path.join(_REPOS_ROOT, name)
            if not os.path.isdir(repo_path):
                return JSONResponse({"success": False, "error": f"repo not found: {name}"}, status_code=404)
            changelog_path = os.path.join(repo_path, "CHANGELOG.md")
            if not os.path.isfile(changelog_path):
                return JSONResponse({"success": False, "error": f"No CHANGELOG.md for {name}"})
            try:
                with open(changelog_path, encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError) as e:
                return JSONResponse({"success": False, "error": str(e)})
            return JSONResponse({"success": True, "repo": name, "content": content})

        for route in [
            Route("/health", endpoint=health),
            Route("/status", endpoint=status),
            Route("/activity", endpoint=activity),
            Route("/dirty", endpoint=dirty),
            Route("/builds", endpoint=builds_endpoint),
            Route("/sessions", endpoint=sessions_endpoint),
            Route("/portmap", endpoint=portmap),
            Route("/backend-health", endpoint=backend_health),
            Route("/tools", endpoint=tools),
            Route("/deps", endpoint=deps),
            Route("/repo", endpoint=repo),
            Route("/buildlog", endpoint=buildlog),
            Route("/changelog", endpoint=changelog),
        ]:
            app.router.routes.append(route)

        logger.info("Starting fleetwatcher HTTP on %s:%s", host, port)
        uvicorn.run(app, host=host, port=int(port), log_level="info")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
