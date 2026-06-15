"""Sync agent state with a dedicated git branch for cross-run persistence.

State is stored on the `agent-state` branch in the agent's own repo.
On start: fetch state file from branch (if exists).
On save: push updated state file back to branch.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

STATE_BRANCH = "agent-state"
STATE_FILE = "agent-state.json"


def pull_state(repo_dir: str | Path, dest: str | Path) -> bool:
    """Fetch state file from agent-state branch. Returns True if found."""
    repo_dir = Path(repo_dir)
    dest = Path(dest)
    try:
        subprocess.run(
            ["git", "fetch", "origin", STATE_BRANCH],
            cwd=repo_dir, capture_output=True, check=False,
        )
        # Try to extract the file from the fetched branch
        result = subprocess.run(
            ["git", "show", f"origin/{STATE_BRANCH}:{STATE_FILE}"],
            cwd=repo_dir, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            dest.write_text(result.stdout, encoding="utf-8")
            return True
    except Exception:
        pass
    return False


def push_state(repo_dir: str | Path, state_path: str | Path) -> bool:
    """Commit and push state file to agent-state branch."""
    repo_dir = Path(repo_dir)
    state_path = Path(state_path)
    if not state_path.exists():
        return False
    try:
        # Create or switch to state branch
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
            # Remove all files from orphan branch
            subprocess.run(
                ["git", "rm", "-rf", "."],
                cwd=repo_dir, capture_output=True, check=False,
            )

        # Copy state file in
        dest = repo_dir / STATE_FILE
        dest.write_bytes(state_path.read_bytes())

        # Commit and push
        subprocess.run(
            ["git", "add", STATE_FILE],
            cwd=repo_dir, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"update state [skip ci]"],
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
        # Switch back to original branch
        original = os.environ.get("GITHUB_REF_NAME", "master")
        subprocess.run(
            ["git", "checkout", original],
            cwd=repo_dir, capture_output=True, check=False,
        )
