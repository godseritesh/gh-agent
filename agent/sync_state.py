"""Sync agent state with a dedicated git branch for cross-run persistence.

State is stored on the `agent-state` branch in the agent's own repo.
On start: fetch state file from branch (if exists).
On save: push updated state file back to branch.

Persists:
  - agent-state.json  (run state, last checked commits, token budget)
  - AGENTS-<repo>.md  (per-repo context knowledge base)
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

STATE_BRANCH = "agent-state"
STATE_FILE = "agent-state.json"


def _files_to_sync(repo_dir: Path) -> list[Path]:
    """Find all state files: agent-state.json + AGENTS-*.md + INDEX-*.json"""
    files = []
    state_file = repo_dir / STATE_FILE
    if state_file.exists():
        files.append(state_file)
    for agents_file in repo_dir.glob("AGENTS-*.md"):
        files.append(agents_file)
    for index_file in repo_dir.glob("INDEX-*.json"):
        files.append(index_file)
    return files


def pull_state(repo_dir: str | Path) -> bool:
    """Fetch state files from agent-state branch. Returns True if any found."""
    repo_dir = Path(repo_dir)
    found = False
    try:
        subprocess.run(
            ["git", "fetch", "origin", STATE_BRANCH],
            cwd=repo_dir, capture_output=True, check=False,
        )
        # Pull state.json
        result = subprocess.run(
            ["git", "show", f"origin/{STATE_BRANCH}:{STATE_FILE}"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            (repo_dir / STATE_FILE).write_text(result.stdout, encoding="utf-8")
            found = True

        # Pull AGENTS-*.md + INDEX-*.json files
        tree = subprocess.run(
            ["git", "ls-tree", "--name-only", f"origin/{STATE_BRANCH}"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        )
        if tree.returncode == 0:
            for name in tree.stdout.strip().split("\n"):
                name = name.strip()
                if not name:
                    continue
                is_agents = name.startswith("AGENTS-") and name.endswith(".md")
                is_index = name.startswith("INDEX-") and name.endswith(".json")
                if is_agents or is_index:
                    result = subprocess.run(
                        ["git", "show", f"origin/{STATE_BRANCH}:{name}"],
                        cwd=repo_dir, capture_output=True, text=True, check=False,
                    )
                    if result.returncode == 0:
                        (repo_dir / name).write_text(result.stdout, encoding="utf-8")
                        found = True
    except Exception:
        pass
    return found


def push_state(repo_dir: str | Path) -> bool:
    """Commit and push all state files to agent-state branch."""
    repo_dir = Path(repo_dir)
    files = _files_to_sync(repo_dir)
    if not files:
        return False

    original_branch = os.environ.get("GITHUB_REF_NAME", "master")

    try:
        # Check if state branch exists
        has_branch = subprocess.run(
            ["git", "rev-parse", "--verify", STATE_BRANCH],
            cwd=repo_dir, capture_output=True, check=False,
        ).returncode == 0

        if has_branch:
            subprocess.run(
                ["git", "checkout", STATE_BRANCH],
                cwd=repo_dir, capture_output=True, check=True,
            )
        else:
            subprocess.run(
                ["git", "checkout", "--orphan", STATE_BRANCH],
                cwd=repo_dir, capture_output=True, check=True,
            )
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=repo_dir, capture_output=True, check=False,
            )

        # Copy all state files in
        for f in files:
            dest = repo_dir / f.name
            dest.write_bytes(f.read_bytes())
            subprocess.run(
                ["git", "add", f.name],
                cwd=repo_dir, capture_output=True, check=False,
            )

        subprocess.run(
            ["git", "commit", "-m", "update state [skip ci]"],
            cwd=repo_dir, capture_output=True, check=False,
        )
        subprocess.run(
            ["git", "push", "origin", STATE_BRANCH],
            cwd=repo_dir, capture_output=True, check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        subprocess.run(
            ["git", "checkout", original_branch],
            cwd=repo_dir, capture_output=True, check=False,
        )
