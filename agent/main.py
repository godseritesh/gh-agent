from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from agent import agents_md
from agent.coder import apply_patch, implement_step, run_linter, run_tests
from agent.config import AgentConfig
from agent.hf_client import HFClient
from agent.planner import analyze_repo, create_plan, pick_best_suggestion
from agent.pr import (
    commit_and_push,
    create_pr_body,
    create_pr_branch,
    create_pull_request,
    enable_auto_merge,
)
from agent.scanner import RepoAnalysis, clone_or_pull
from agent.state import AgentState
from agent.sync_state import pull_state

ORG = "godseritesh"
WORKSPACE = Path("/tmp/agent-repos")
STATE_PATH = Path("agent-state.json")
CONFIG_PATH = Path(".agent-config.yaml")
AGENT_REPO = Path(os.environ.get("AGENT_REPO_DIR", "."))
MAX_ITERATIONS = 3


def _get_last_commit(repo_dir: Path) -> str | None:
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else None


def process_repo(
    client: HFClient,
    repo_name: str,
    repo_config: AgentConfig,
    state: AgentState,
    agents_context: dict[str, str],
    repo_index: dict | None = None,
) -> str | None:
    print(f"\n=== Researching {repo_name} ===")
    agents_file = AGENT_REPO / agents_md.filename(repo_name)

    # 1. Check if we have cached context
    existing_context = agents_context.get(repo_name, "")
    last_commit = state.get_last_commit(repo_name)

    if existing_context and last_commit:
        # Quick check: has anything changed?
        clone_dir = clone_or_pull(ORG, repo_name, WORKSPACE)
        current_commit = _get_last_commit(clone_dir)
        if current_commit == last_commit:
            print(f"  No new commits since last check ({last_commit[:8]}), using cached context")
            analysis = RepoAnalysis(repo_name, clone_dir)
            analysis.lint_output = ""
            if repo_config and repo_config.lint_command:
                analysis.run_linter(repo_config.lint_command)
        else:
            print(f"  New commit {current_commit[:8]} (was {last_commit[:8]}), partial re-scan")
            analysis = RepoAnalysis(repo_name, clone_dir)
            analysis.detect_stack()
            analysis.read_key_files()
            analysis.detect_ci()
            if repo_config and repo_config.lint_command:
                analysis.run_linter(repo_config.lint_command)
    else:
        clone_dir = clone_or_pull(ORG, repo_name, WORKSPACE)
        analysis = RepoAnalysis(repo_name, clone_dir)
        analysis.detect_stack()
        analysis.build_file_tree()
        analysis.read_key_files()
        analysis.detect_ci()
        if repo_config and repo_config.lint_command:
            analysis.run_linter(repo_config.lint_command)

    if repo_index:
        analysis.load_index(repo_index)

    state.mark_repo_seen(repo_name)
    print(f"  Stack: {', '.join(analysis.tech_stack) or 'unknown'}")
    print(f"  Files: {analysis.total_files}, Lines: {analysis.total_lines}")
    print(f"  Tests: {analysis.test_file_count}")

    # 2. Send to LLM for improvement suggestions
    context_input = analysis.to_context()
    if existing_context:
        context_input = existing_context + "\n\n## Current Analysis\n" + context_input[:4000]

    suggestions = analyze_repo(client, analysis)
    if not suggestions:
        print("  No improvement suggestions from LLM")
        agents_md.save(existing_context or agents_md.generate_initial_context(
            repo_name, analysis, []), agents_file)
        return None

    print(f"  Got {len(suggestions)} suggestions:")
    for s in suggestions:
        print(f"    [{s.get('impact','?')}] {s.get('title','?')} ({s.get('effort','?')})")

    # 3. Pick best suggestion
    best = pick_best_suggestion(suggestions, max_effort="medium")
    if not best:
        print("  No suggestions fit within effort budget")
        agents_md.save(existing_context or agents_md.generate_initial_context(
            repo_name, analysis, suggestions), agents_file)
        return None

    print(f"\n=== Implementing: {best['title']} ===")

    # 4. Check token budget before planning
    if not state.can_use_tokens(500):
        print("  Token budget insufficient for planning, skipping")
        return None

    valid_files = _get_valid_files(clone_dir)
    plan = create_plan(client, repo_name, best, valid_files)
    if not plan:
        print("  No plan generated")
        return None
    print(f"  Plan: {[s['step'] for s in plan]}")

    # 5. Feature branch
    ts = int(__import__("time").time())
    branch = f"agent-{best.get('category','improvement')}-{repo_name.lower()}-{ts}"
    create_pr_branch(str(clone_dir), branch)

    # Ensure git user config is set in target repo
    subprocess.run(
        ["git", "config", "user.name", "godseritesh"], cwd=clone_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "riteshgodse008@gmail.com"],
        cwd=clone_dir, capture_output=True)

    # 6. Implement each step
    build_context = _get_build_context(clone_dir, analysis)
    changed = False
    for subtask in plan[:MAX_ITERATIONS]:
        files = subtask.get("files", [])
        for f in files:
            filepath = clone_dir / f

            code = filepath.read_text(encoding="utf-8") if filepath.exists() else ""
            if not state.can_use_tokens(len(code)):
                print("  Token budget exceeded, stopping")
                return None

            lang = _detect_language(f)
            state.start_task(f"{repo_name}:{f}")
            try:
                new_code = implement_step(
                    client, repo_name, subtask["step"], f, code, lang, build_context,
                )
                if not new_code.strip():
                    print(f"  [debug] empty output for {f}")
                elif new_code != code:
                    apply_patch(filepath, new_code)
                    changed = True
                    print(f"  [modified] {f}")
                state.record_tokens(len(code) + len(new_code))

                tf = repo_config.test_framework if repo_config else None
                lc = repo_config.lint_command if repo_config else None
                _, test_out = run_tests(clone_dir, tf)
                lint_code, lint_out = run_linter(clone_dir, lc)

                if test_out.strip():
                    print(f"  Tests: {test_out[:200]}")
                if lint_code != 0:
                    print(f"  Lint issues: {lint_out[:200]}")
            finally:
                state.finish_task()

    if not changed:
        print("  No files were modified, skipping PR")
        return None

    # 7. Build verification before commit
    if repo_config and repo_config.build_command:
        print(f"  Verifying build: {repo_config.build_command}")
        build_result = subprocess.run(
            repo_config.build_command.split(),
            capture_output=True, text=True, cwd=str(clone_dir), timeout=120,
        )
        if build_result.returncode != 0:
            build_output = build_result.stdout + build_result.stderr
            print(f"  Build FAILED (skipping PR):\n{build_output[:500]}")
            changed = False
            return None
        print("  Build OK")

    # 8. Create PR
    commit_message = f"agent: {best.get('rationale', best['title'])[:72]}"
    commit_and_push(str(clone_dir), commit_message)

    pr_body_data = {
        "problem": best.get("rationale", best["title"]),
        "change": "\n".join(f"- {s['step']}" for s in plan),
        "testing": "Tests and linter run; results in run log",
        "risk": best.get("impact", "medium"),
    }
    body = create_pr_body(pr_body_data)
    pr_url = create_pull_request(
        str(clone_dir), f"[agent] {best['title']}", body, "master",
    )
    if pr_url and repo_config and repo_config.has_tests:
        enable_auto_merge(str(clone_dir), _extract_pr_number(pr_url))

    state.set_last_commit(repo_name, "HEAD")

    # 9. Update AGENTS.md with shipped entry
    shipped_entry = {
        "title": best["title"],
        "repo": repo_name,
        "category": best.get("category", "improvement"),
        "impact": best.get("impact", "medium"),
        "rationale": best.get("rationale", ""),
        "pr_url": pr_url or "N/A",
    }
    state.record_shipped(shipped_entry)

    if existing_context:
        new_context = agents_md.append_shipped_entry(existing_context, shipped_entry)
    else:
        new_context = agents_md.generate_initial_context(repo_name, analysis, suggestions)
        new_context = agents_md.append_shipped_entry(new_context, shipped_entry)

    agents_md.save(new_context, agents_file)
    print("  AGENTS.md updated with shipped entry")
    return pr_url


def _detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".jsx": "javascript", ".java": "java",
        ".kt": "kotlin", ".go": "go", ".rs": "rust",
        ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".md": "markdown", ".html": "html", ".css": "css",
        ".sql": "sql", ".sh": "bash", ".tf": "hcl",
    }.get(ext, "text")


def _extract_pr_number(pr_url: str) -> int:
    return int(pr_url.rstrip("/").split("/")[-1])


def _get_build_context(clone_dir: Path, analysis: RepoAnalysis) -> str:
    """Read project build file content to prevent hallucinated imports."""
    for name in ["pom.xml", "build.gradle", "package.json", "Cargo.toml", "pyproject.toml"]:
        content = analysis.key_files.get(name)
        if content:
            return content
        p = clone_dir / name
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")[:2000]
    return ""


def _get_valid_files(clone_dir: Path) -> set[str]:
    """Get set of relative file paths in a cloned repo."""
    files: set[str] = set()
    for path in clone_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(clone_dir)
            parts = rel.parts
            if any(p.startswith(".") and p not in (".github",) for p in parts):
                continue
            if any(p in {"__pycache__", "node_modules", "target", "build"} for p in parts):
                continue
            files.add(str(rel.as_posix()))
    return files


def main() -> None:
    pull_state(AGENT_REPO)
    config = AgentConfig.load(CONFIG_PATH)
    state = AgentState.load(STATE_PATH)

    # Load all existing AGENTS.md files
    agents_context: dict[str, str] = {}
    for md_file in AGENT_REPO.glob("AGENTS-*.md"):
        repo_name = md_file.stem.replace("AGENTS-", "", 1)
        agents_context[repo_name] = md_file.read_text(encoding="utf-8")

    hf_token = os.environ.get("HF_TOKEN")
    client = HFClient(
        hf_token,
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        gh_token=os.environ.get("GH_TOKEN"),
    )

    repos_to_process = config.active_repos
    repo_override = os.environ.get("REPO_NAME", "")
    if repo_override:
        repos_to_process = [r for r in repos_to_process if r == repo_override]

    # Load pre-built AST indexes
    indexes: dict[str, dict] = {}
    for idx_file in AGENT_REPO.glob("INDEX-*.json"):
        repo_name = idx_file.stem.replace("INDEX-", "", 1)
        try:
            indexes[repo_name] = json.loads(idx_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    for repo_name in repos_to_process:
        repo_config = config.get(repo_name)
        if not repo_config or not repo_config.active:
            continue

        # Attach pre-built index if available
        repo_index = indexes.get(repo_name)

        try:
            pr_url = process_repo(client, repo_name, repo_config, state, agents_context, repo_index)
            if pr_url:
                print(f"  PR created: {pr_url}")
        except Exception as e:
            print(f"  Failed on {repo_name}: {e}")

    state.save(STATE_PATH)
    client.close()


if __name__ == "__main__":
    main()
