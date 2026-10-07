"""Fleet topology - MCP interdependencies and port mapping."""

import json
import logging
import os
import re
import socket

logger = logging.getLogger("fleetwatcher.graph")


def server_dependencies(root: str) -> dict:
    """Find which MCP servers reference which other MCP servers.

    Scans opencode.jsonc and claude_desktop_config.json across the fleet
    for MCP server-to-server references.
    """
    nodes = set()
    edges = []
    config_sources = _find_configs(root)

    for config_path, config in config_sources:
        servers = _extract_mcp_servers(config)
        for name, _ in servers:
            nodes.add(name)
        # Find intra-fleet references: server A's command references server B's repo
        for name, cfg in servers:
            cmd_str = json.dumps(cfg.get("command", []))
            for other_name, _ in servers:
                if other_name != name and other_name in cmd_str:
                    edges.append({"from": name, "to": other_name, "via": "config_path"})

    return {
        "success": True,
        "data": {
            "nodes": sorted(nodes),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }


def _find_configs(root: str) -> list[tuple[str, dict]]:
    """Find opencode.jsonc and claude_desktop_config.json files."""
    configs = []
    user_home = os.path.expanduser("~")
    candidates = [
        os.path.join(user_home, ".config", "opencode", "opencode.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                configs.append((path, json.load(open(path, encoding="utf-8"))))
            except (json.JSONDecodeError, OSError):
                pass
    return configs


def _extract_mcp_servers(config: dict) -> list[tuple[str, dict]]:
    """Extract MCP server entries from various config formats."""
    servers = []
    mcp_section = config.get("mcp", config.get("mcpServers", {}))
    if isinstance(mcp_section, dict):
        for name, cfg in mcp_section.items():
            if isinstance(cfg, dict) and cfg.get("enabled", True):
                servers.append((name, cfg))
    return servers


def port_map(root: str, registry_path: str) -> dict:
    """Compare live port usage against registered port assignments."""
    registered = _parse_port_registry(registry_path)
    live = _scan_live_ports()
    mapped = []
    for port, expected_repo in registered.items():
        actual = live.get(port)
        mapped.append(
            {
                "port": port,
                "expected": expected_repo,
                "actual_service": actual,
                "match": actual == expected_repo if actual else False,
                "conflict": actual is not None and actual != expected_repo,
            }
        )
    unmapped = {p: s for p, s in live.items() if int(p) not in registered}
    return {
        "success": True,
        "data": {
            "mapped": mapped,
            "unmapped_ports": unmapped,
            "registered_count": len(registered),
            "live_count": len(live),
            "conflicts": sum(1 for m in mapped if m["conflict"]),
        },
    }


_PORT_RE = re.compile(r"\| (\d{4,5}) \| (\S+)")


def _parse_port_registry(path: str) -> dict[int, str]:
    """Parse WEBAPP_PORTS.md into {port: repo} map."""
    registry = {}
    if not os.path.isfile(path):
        return registry
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = _PORT_RE.search(line)
                if m:
                    port = int(m.group(1))
                    if 10700 <= port <= 11500:
                        registry[port] = m.group(2)
    except (OSError, UnicodeDecodeError):
        pass
    return registry


def _scan_live_ports() -> dict[str, str]:
    """Scan common fleet ports for listening processes."""
    live = {}
    for port in range(10700, 11000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.05)
        try:
            result = sock.connect_ex(("127.0.0.1", port))
            if result == 0:
                live[str(port)] = "listening"
        finally:
            sock.close()
    return live
