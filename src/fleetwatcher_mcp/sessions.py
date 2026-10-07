"""Session documentation scanning and search."""

import logging
import os
import time

logger = logging.getLogger("fleetwatcher.sessions")


def recent_sessions(root: str, hours: int = 48) -> dict:
    """Find session docs modified in the last N hours."""
    cutoff = time.time() - (hours * 3600)
    sessions = []
    _walk_sessions(root, root, cutoff, sessions)
    sessions.sort(key=lambda x: x.get("modified_ts", 0), reverse=True)
    return {"success": True, "sessions": sessions, "count": len(sessions)}


def _walk_sessions(root: str, current: str, cutoff: float, results: list):
    """Recursively walk session doc directory."""
    try:
        for name in os.listdir(current):
            full = os.path.join(current, name)
            if os.path.isdir(full):
                _walk_sessions(root, full, cutoff, results)
            elif name.endswith(".md") and name != ".audit.log":
                mtime = os.path.getmtime(full)
                if mtime >= cutoff:
                    rel = os.path.relpath(full, root)
                    try:
                        with open(full, encoding="utf-8") as f:
                            first_line = f.readline().strip()
                    except (OSError, UnicodeDecodeError):
                        first_line = ""
                    results.append(
                        {
                            "path": rel,
                            "title": first_line.lstrip("# "),
                            "modified_ts": mtime,
                            "size": os.path.getsize(full),
                        }
                    )
    except (PermissionError, FileNotFoundError):
        pass


def search_sessions(root: str, query: str) -> dict:
    """Full-text search across session doc content."""
    results = []
    query_lower = query.lower()
    _search_walk(root, root, query_lower, results)
    return {"success": True, "sessions": results, "count": len(results)}


def _search_walk(root: str, current: str, query: str, results: list):
    try:
        for name in os.listdir(current):
            full = os.path.join(current, name)
            if os.path.isdir(full):
                _search_walk(root, full, query, results)
            elif name.endswith(".md") and name != ".audit.log":
                try:
                    with open(full, encoding="utf-8") as f:
                        content = f.read()
                    if query in content.lower():
                        rel = os.path.relpath(full, root)
                        lines = content.count("\n") + 1
                        results.append(
                            {
                                "path": rel,
                                "title": content.split("\n")[0].lstrip("# "),
                                "lines": lines,
                                "size": len(content),
                            }
                        )
                except (OSError, UnicodeDecodeError):
                    pass
    except (PermissionError, FileNotFoundError):
        pass
