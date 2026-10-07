"""Fleet repo pulse - activity, status, dirty state."""

import logging
import os
import subprocess
import time

logger = logging.getLogger("fleetwatcher.pulse")

_REPOS_ROOT_OVERRIDE: str | None = None


def _repos_root(base: str) -> str:
    return _REPOS_ROOT_OVERRIDE or base


def _list_repos(root: str) -> list[str]:
    """List directories under root that look like git repos."""
    repos = []
    try:
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isdir(os.path.join(full, ".git")):
                repos.append(name)
    except FileNotFoundError:
        pass
    return sorted(repos)


def _description(repo_path: str) -> str:
    """Best-effort one-line description of a repo."""
    import json as _json
    import re as _re

    pyproject = os.path.join(repo_path, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            with open(pyproject, encoding="utf-8") as f:
                m = _re.search(r'^description\s*=\s*"([^"]+)"', f.read(), _re.M)
            if m:
                return m.group(1)
        except OSError:
            pass
    pkg = os.path.join(repo_path, "package.json")
    if os.path.isfile(pkg):
        try:
            with open(pkg, encoding="utf-8") as f:
                data = _json.load(f)
            if data.get("description"):
                return data["description"]
        except (OSError, _json.JSONDecodeError):
            pass
    for readme in ("README.md", "AGENTS.md", "CLAUDE.md"):
        path = os.path.join(repo_path, readme)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if (
                            s
                            and not s.startswith("#")
                            and not s.startswith("[![")
                            and not s.startswith("|")
                        ):
                            return s[:200]
            except OSError:
                pass
    return ""


def _github_url(repo_path: str) -> str:
    """Convert git remote origin to an https://github.com/owner/repo URL."""
    import re as _re

    url = _git(repo_path, "remote", "get-url", "origin")
    if not url:
        return ""
    m = _re.search(r"(?:git@|https?://)github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", url)
    return f"https://github.com/{m.group(1)}" if m else ""


def _git(repo_path: str, *args: str) -> str | None:
    """Run git command, return stdout or None on failure."""
    if not os.path.isdir(repo_path):
        return None
    try:
        result = subprocess.run(
            ["git", *list(args)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=repo_path,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError):
        return None


def recent_activity(root: str, hours: int = 24) -> dict:
    """Find repos with activity in the last N hours."""
    root = _repos_root(root)
    time.time() - (hours * 3600)
    active = []
    for name in _list_repos(root):
        repo_path = os.path.join(root, name)
        last_commit = _git(repo_path, "log", "-1", "--format=%ct:%s", "--since", f"{hours}hours ago")
        if last_commit:
            parts = last_commit.split(":", 1)
            ts = int(parts[0]) if parts[0].isdigit() else 0
            msg = parts[1] if len(parts) > 1 else ""
            active.append(
                {
                    "repo": name,
                    "description": _description(repo_path),
                    "last_commit_ts": ts,
                    "last_commit_msg": msg,
                    "has_nopublish": os.path.isfile(os.path.join(repo_path, ".nopublish")),
                    "has_ai_readiness": os.path.isfile(os.path.join(repo_path, ".ai-readiness")),
                }
            )
        else:
            assfix = os.path.join(repo_path, ".assess-fix-timestamp")
            if os.path.isfile(assfix):
                try:
                    import json

                    data = json.load(open(assfix, encoding="utf-8"))
                    ts = data.get("timestamp", "")
                    active.append(
                        {
                            "repo": name,
                            "description": _description(repo_path),
                            "last_assfix_ts": ts,
                            "has_nopublish": os.path.isfile(os.path.join(repo_path, ".nopublish")),
                        }
                    )
                except (json.JSONDecodeError, OSError):
                    pass
    return {"success": True, "repos": active, "count": len(active)}


def repo_status(repo_path: str) -> dict:
    """Detailed status for a single repo."""
    import datetime as _dt

    name = os.path.basename(repo_path)
    last_commit = _git(repo_path, "log", "-1", "--format=%H:%ct:%s")
    branch = _git(repo_path, "branch", "--show-current")
    has_remote = bool(_git(repo_path, "remote", "-v"))
    status_output = _git(repo_path, "status", "--porcelain")
    dirty = bool(status_output) if status_output else False
    commit_count = _git(repo_path, "rev-list", "--count", "HEAD")

    result = {
        "repo": name,
        "branch": branch or "unknown",
        "has_remote": has_remote,
        "dirty": dirty,
        "has_nopublish": os.path.isfile(os.path.join(repo_path, ".nopublish")),
        "has_ai_readiness": os.path.isfile(os.path.join(repo_path, ".ai-readiness")),
        "has_assfix_timestamp": os.path.isfile(os.path.join(repo_path, ".assess-fix-timestamp")),
        "has_build_log": os.path.isfile(os.path.join(repo_path, "BUILD_LOG.md")),
        "has_changelog": os.path.isfile(os.path.join(repo_path, "CHANGELOG.md")),
        "has_tauri": os.path.isdir(os.path.join(repo_path, "native"))
        or os.path.isdir(os.path.join(repo_path, "web_sota", "src-tauri")),
        "description": _description(repo_path),
        "github_url": _github_url(repo_path),
        "commit_count": int(commit_count) if commit_count and commit_count.isdigit() else None,
    }
    if last_commit:
        parts = last_commit.split(":", 2)
        result["last_commit_hash"] = parts[0]
        result["last_commit_ts"] = int(parts[1]) if parts[1].isdigit() else 0
        result["last_commit_msg"] = parts[2] if len(parts) > 2 else ""
        ts = result["last_commit_ts"]
        result["last_commit_iso"] = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
    return {"success": True, **result}


def dirty_repos(root: str) -> dict:
    """List repos with uncommitted changes."""
    root = _repos_root(root)
    dirty = []
    for name in _list_repos(root):
        repo_path = os.path.join(root, name)
        status = _git(repo_path, "status", "--porcelain")
        if status:
            lines = [l for l in status.split("\n") if l.strip()]
            dirty.append({"repo": name, "description": _description(repo_path), "changed_files": len(lines)})
    return {"success": True, "repos": dirty, "count": len(dirty)}
