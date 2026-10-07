# fleetwatcher-mcp

Internal fleet pulse — monitor repos, builds, sessions, topology, and backend liveness.

Observer only: reports health, never restarts anything. Actuation stays in
windows-operations-mcp (winops_svc) or manual `sc.exe`.

## Tools

| Tool | What it does |
|------|-------------|
| `fleet_pulse` | Monitor repo activity (recent commits, dirty state, sentinels) |
| `build_watch` | Parse BUILD_LOG.md across the fleet for NSIS build outcomes |
| `session_scan` | Search and browse agent session documentation |
| `fleet_graph` | MCP dependencies, live port mapping, and backend health (TCP + PID + read-only service state + HTTP probe) |
| `fleetwatcher_help` / `fleetwatcher_status` | Help and health |

## Backend health verdicts

`healthy | degraded | dead | listening-but-hung | unbound | conflict | unknown-listening`.
Each dead/hung row carries an NSSM-safe `sc.exe stop/start` suggestion string
(never executed — verify a NEW PID owns the port, never taskkill the child).

## Quick Start

```powershell
.\start.ps1
```

Starts backend on port 10918 and Fleet Pulse dashboard on port 10919.

## Config

Environment variables: see `llms-full.txt`.

## Ports

- 10918: backend (FastMCP HTTP + REST)
- 10919: Fleet Pulse dashboard (Vite + React)
