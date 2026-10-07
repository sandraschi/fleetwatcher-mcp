"""Build monitoring - NSIS builds, CUA smoke tests."""

import logging
import os

logger = logging.getLogger("fleetwatcher.builds")


def recent_builds(root: str, limit: int = 20) -> dict:
    """Parse BUILD_LOG.md across fleet repos, return recent entries."""
    builds = []
    for name in sorted(os.listdir(root)):
        repo_path = os.path.join(root, name)
        build_log = os.path.join(repo_path, "BUILD_LOG.md")
        if not os.path.isfile(build_log):
            continue
        try:
            lines = []
            with open(build_log, encoding="utf-8") as f:
                lines = f.readlines()
            entries = _parse_build_log(lines, limit)
            for e in entries:
                e["repo"] = name
            builds.extend(entries)
        except (OSError, UnicodeDecodeError):
            pass
    builds.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"success": True, "builds": builds[:limit], "count": min(len(builds), limit)}


def _parse_build_log(lines: list[str], limit: int) -> list[dict]:
    """Parse markdown build log entries."""
    entries = []
    current: dict | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current and current.get("timestamp"):
                entries.append(current)
            current = {"timestamp": stripped[3:].strip()}
        elif stripped.startswith("- ") and current is not None:
            key_val = stripped[2:].split(":", 1)
            if len(key_val) == 2:
                current[key_val[0].strip().lower().replace(" ", "_")] = key_val[1].strip()
    if current and current.get("timestamp"):
        entries.append(current)
    return entries


def build_log(root: str, repo_name: str) -> dict:
    """Return full BUILD_LOG.md content for a repo."""
    repo_path = os.path.join(root, repo_name)
    build_log = os.path.join(repo_path, "BUILD_LOG.md")
    if not os.path.isfile(build_log):
        return {"success": False, "error": f"No BUILD_LOG.md found for {repo_name}"}
    with open(build_log, encoding="utf-8") as f:
        content = f.read()
    return {"success": True, "repo": repo_name, "content": content}
