from __future__ import annotations

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


def create_pr_branch(repo_dir: str, branch_name: str) -> None:
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo_dir, capture_output=True, check=True,
    )


def commit_and_push(repo_dir: str, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=repo_dir, capture_output=True, check=True)


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
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def enable_auto_merge(repo_dir: str, pr_number: int) -> bool:
    result = subprocess.run(
        ["gh", "pr", "merge", str(pr_number), "--auto", "--squash"],
        cwd=repo_dir, capture_output=True,
    )
    return result.returncode == 0
