from __future__ import annotations

import os
import subprocess
from typing import Any

PR_TEMPLATE = """## Problem

{problem}

## Change

{change}

## Testing

{testing}

## Risk

{risk}
"""


def _get_token() -> str | None:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _inject_token_into_remote(repo_dir: str) -> None:
    """Inject GH_TOKEN into the remote URL so git push can authenticate."""
    token = _get_token()
    if not token:
        return
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return
    url = result.stdout.strip()
    if "://" not in url:
        return  # SSH, skip
    # Always rewrite the remote URL with the PAT, even if already authed
    _, _, rest = url.partition("://")
    host_path = rest.split("@", 1)[-1]  # strip any existing token
    updated = f"https://x-access-token:{token}@{host_path}"
    subprocess.run(
        ["git", "remote", "set-url", "origin", updated],
        cwd=repo_dir, capture_output=True,
    )


def create_pr_branch(repo_dir: str, branch_name: str) -> None:
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo_dir, capture_output=True, check=True,
    )
    _inject_token_into_remote(repo_dir)


def commit_and_push(repo_dir: str, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, capture_output=True, check=True)
    result = subprocess.run(
        ["git", "push", "origin", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  Push failed: {result.stderr.strip()[:200]}")


def create_pr_body(plan: dict[str, Any]) -> str:
    return PR_TEMPLATE.format(
        problem=plan.get("problem", "No description"),
        change=plan.get("change", "No details"),
        testing=plan.get("testing", "Tests passed"),
        risk=plan.get("risk", "Low"),
    )


def create_pull_request(repo_dir: str, title: str, body: str, base: str = "master") -> str | None:
    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", base,
        ],
        cwd=repo_dir, capture_output=True, text=True,
        env={**os.environ, "GITHUB_TOKEN": _get_token() or ""},
    )
    if result.returncode != 0:
        print(f"  PR creation failed: {result.stderr.strip()[:200]}")
        return None
    return result.stdout.strip()


def enable_auto_merge(repo_dir: str, pr_number: int) -> bool:
    result = subprocess.run(
        ["gh", "pr", "merge", str(pr_number), "--auto", "--squash"],
        cwd=repo_dir, capture_output=True,
    )
    return result.returncode == 0
