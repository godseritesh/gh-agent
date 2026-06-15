from __future__ import annotations

import os
from pathlib import Path

from agent.coder import apply_patch, generate_fix, run_linter, run_tests
from agent.config import AgentConfig
from agent.hf_client import HFClient
from agent.planner import classify_issue, create_plan
from agent.pr import (
    commit_and_push,
    create_pr_body,
    create_pr_branch,
    create_pull_request,
    enable_auto_merge,
)
from agent.scanner import RepoInfo, clone_or_pull, scan_repo
from agent.state import AgentState
from agent.sync_state import pull_state, push_state

ORG = "godseritesh"
WORKSPACE = Path("/tmp/agent-repos")
STATE_PATH = Path("agent-state.json")
CONFIG_PATH = Path(".agent-config.yaml")
AGENT_REPO = Path(os.environ.get("AGENT_REPO_DIR", "."))
MAX_ITERATIONS = 3


def main() -> None:
    pull_state(AGENT_REPO, STATE_PATH)
    config = AgentConfig.load(CONFIG_PATH)
    state = AgentState.load(STATE_PATH)
    hf_token = os.environ.get("HF_TOKEN")
    client = HFClient(hf_token)

    repo_name = os.environ.get("REPO_NAME", "")

    if repo_name and repo_name in config.repos:
        repos_to_process = [repo_name]
    else:
        repos_to_process = config.active_repos

    for repo_name in repos_to_process:
        repo_config = config.get(repo_name)
        if not repo_config or not repo_config.active:
            continue

        print(f"Processing {repo_name}...")

        try:
            clone_dir = clone_or_pull(ORG, repo_name, WORKSPACE)
        except Exception as e:
            print(f"  Failed to clone/pull {repo_name}: {e}")
            continue

        base_commit = state.get_last_commit(repo_name)
        try:
            changed_files = scan_repo(RepoInfo(repo_name, clone_dir), base_commit)
        except Exception as e:
            print(f"  Failed to scan {repo_name}: {e}")
            changed_files = []

        if not changed_files:
            print(f"No changes in {repo_name}")
            continue

        description = os.environ.get("ISSUE_DESCRIPTION", f"Changes in {', '.join(changed_files)}")

        classification = classify_issue(client, description)
        pri = classification.get("priority", "unknown")
        cat = classification.get("category", "unknown")
        print(f"Classified as {pri} priority: {cat}")

        plan = create_plan(client, repo_name, description, changed_files)
        if not plan:
            print(f"No plan generated for {repo_name}")
            continue

        branch = f"agent-fix-{repo_name.lower()}-{int(__import__('time').time())}"
        create_pr_branch(str(clone_dir), branch)

        for subtask in plan[:MAX_ITERATIONS]:
            files = subtask.get("files", [])
            for f in files:
                filepath = clone_dir / f
                if not filepath.exists():
                    print(f"  File {f} not found, skipping")
                    continue

                code = filepath.read_text(encoding="utf-8")
                if not state.can_use_tokens(len(code)):
                    print("  Token budget exceeded, stopping")
                    break

                state.start_task(f"{repo_name}:{f}")
                fix = generate_fix(client, repo_name, subtask["step"], f, code)
                apply_patch(filepath, fix)
                state.record_tokens(len(code) + len(fix))

                test_code, test_out = run_tests(clone_dir, repo_config.test_framework)
                lint_code, lint_out = run_linter(clone_dir, repo_config.lint_command)

                if test_code != 0:
                    print(f"  Tests failed, iteration limit: {test_out[:200]}")
                state.finish_task()

        commit_message = f"agent: {classification.get('explanation', description)[:72]}"
        commit_and_push(str(clone_dir), commit_message)

        pr_body_data = {
            "problem": description,
            "change": "\n".join(f"- {s['step']}" for s in plan),
            "testing": "Test and lint results logged in run output",
            "risk": classification.get("priority", "medium"),
        }
        body = create_pr_body(pr_body_data)
        base = repo_config.get("base_branch", "master") if hasattr(repo_config, "get") else "master"
        pr_url = create_pull_request(str(clone_dir), f"[agent] {commit_message}", body, base)
        if pr_url and repo_config.has_tests:
            enable_auto_merge(str(clone_dir), int(pr_url.rstrip("/").split("/")[-1]))

        state.set_last_commit(repo_name, "HEAD")

    state.save(STATE_PATH)
    push_state(AGENT_REPO, STATE_PATH)
    client.close()


if __name__ == "__main__":
    main()
