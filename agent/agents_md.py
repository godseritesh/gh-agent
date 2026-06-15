"""AGENTS.md system: per-repo context cache.

Each repo gets an AGENTS-<repo>.md file stored on the agent-state branch.
On first run: deep analysis is written to this file.
On subsequent runs: the file is loaded to avoid re-scanning the full codebase.
After each successful PR merge: a "features shipped" entry is appended.

This reduces token usage and provides growing context about each repo."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def filename(repo: str) -> str:
    return f"AGENTS-{repo}.md"


def generate_initial_context(repo: str, analysis: Any, suggestions: list[dict]) -> str:
    """Create the initial AGENTS.md for a repo after first deep analysis."""
    lines = [
        f"# {repo} — Agent Knowledge Base",
        "",
        f"Initialized: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Tech Stack",
        f"- {', '.join(analysis.tech_stack) if analysis.tech_stack else 'Unknown'}",
        "",
        "## Codebase Overview",
        f"- Total files: {analysis.total_files}",
        f"- Total lines: {analysis.total_lines}",
        f"- Test files detected: {analysis.test_file_count}",
        f"- CI configs: {', '.join(analysis.ci_files) if analysis.ci_files else 'None'}",
        "",
        "## Key Files",
    ]
    for name, content in analysis.key_files.items():
        preview = content[:500].replace("\n", "\n  ")
        lines.append(f"\n### {name}\n```\n{preview}\n```")

    lines.extend([
        "",
        "## Lint Baseline",
        analysis.lint_output[:1000] if analysis.lint_output else "No linter configured",
        "",
        "## Improvement Suggestions (from initial scan)",
    ])
    for s in suggestions:
        lines.append(f"- [{s.get('impact', '?')}] {s.get('title', '?')} "
                      f"(effort: {s.get('effort', '?')}) — {s.get('rationale', '')}")

    lines.extend([
        "",
        "## Shipped Features & Changes",
        "",
    ])
    return "\n".join(lines)


def append_shipped_entry(context: str, entry: dict[str, Any]) -> str:
    """Append a shipped feature entry to existing AGENTS.md context."""
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        "",
        f"### {date}: {entry.get('title', 'Change')}",
        f"- **Category:** {entry.get('category', 'improvement')}",
        f"- **Impact:** {entry.get('impact', 'medium')}",
        f"- **Rationale:** {entry.get('rationale', '')}",
        f"- **PR URL:** {entry.get('pr_url', 'N/A')}",
        "",
    ]
    return context.rstrip() + "\n" + "\n".join(lines)


def load(path: str | Path) -> str:
    """Load AGENTS.md content from file."""
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def save(context: str, path: str | Path) -> None:
    """Save AGENTS.md content to file."""
    Path(path).write_text(context, encoding="utf-8")


def get_context_for_llm(context: str, max_chars: int = 4000) -> str:
    """Extract the most relevant parts of AGENTS.md for LLM context window."""
    if not context:
        return ""
    # Keep header info + shipped features, limit to max_chars
    return context[:max_chars]
