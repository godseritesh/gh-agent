"""AGENTS.md system: per-repo context cache with tiered hierarchy.

Each repo gets an AGENTS-<repo>.md file stored on the agent-state branch.
The file has a tiered structure for token-efficient loading:
  Tier 1 (always loaded): Summary, Key Facts, Shipped Features
  Tier 2 (loaded if space): File Tree, Lint Baseline
  Tier 3 (loaded if lots of space): Key Files, Archived Suggestions"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SECTIONS = [
    "Summary", "Key Facts", "Shipped Features",
    "File Tree", "Lint Baseline", "Key Files", "Archived Suggestions",
]
TIER1_CHARS = 800  # always load this much from top


def filename(repo: str) -> str:
    return f"AGENTS-{repo}.md"


def generate_initial_context(repo: str, analysis: Any, suggestions: list[dict]) -> str:
    analysis_lines = _build_analysis_lines(analysis)
    lines = [
        f"# {repo} — Agent Knowledge Base",
        "",
        f"Initialized: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Summary",
        f"Stack: {', '.join(analysis.tech_stack) if analysis.tech_stack else 'Unknown'}",
        f"Files: {analysis.total_files}, Lines: {analysis.total_lines}",
        f"Tests detected: {analysis.test_file_count}",
        f"CI configs: {', '.join(analysis.ci_files) if analysis.ci_files else 'None'}",
        "",
        "## Key Facts",
        "",
        "## Shipped Features",
        "",
        "## File Tree",
    ]
    lines.extend(analysis_lines.get("file_tree", []))
    lines.append("")
    lines.append("## Lint Baseline")
    lines.append(analysis.lint_output[:1000] if analysis.lint_output else "No linter configured")
    lines.append("")
    lines.append("## Key Files")
    for name, content in analysis.key_files.items():
        preview = content[:500].replace("\n", "\n  ")
        lines.append(f"\n### {name}\n```\n{preview}\n```")
    lines.append("")
    lines.append("## Archived Suggestions")
    for s in suggestions:
        lines.append(f"- [{s.get('impact', '?')}] {s.get('title', '?')} "
                      f"(effort: {s.get('effort', '?')}) — {s.get('rationale', '')}")
    lines.append("")
    return "\n".join(lines)


def _build_analysis_lines(analysis: Any) -> dict[str, list[str]]:
    lines: dict[str, list[str]] = {"file_tree": []}
    tree = analysis.file_tree if hasattr(analysis, "file_tree") else ""
    lines["file_tree"].append(f"```\n{tree[:2000]}\n```" if tree else "(empty)")
    return lines


def append_shipped_entry(context: str, entry: dict[str, Any]) -> str:
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
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def save(context: str, path: str | Path) -> None:
    Path(path).write_text(context, encoding="utf-8")


def get_context_for_llm(context: str, max_chars: int = 4000) -> str:
    if not context:
        return ""
    if len(context) <= max_chars:
        return context
    result_parts: list[str] = []
    remaining = max_chars
    for section in _iter_sections(context):
        if remaining <= 0:
            break
        if section["name"] in ("Summary", "Key Facts", "Shipped Features"):
            take = min(len(section["text"]), remaining)
            result_parts.append(section["text"][:take])
            remaining -= take
        elif section["name"] in ("File Tree", "Lint Baseline"):
            if remaining > TIER1_CHARS:
                full = section["text"]
                take = min(len(full), remaining)
                result_parts.append(full[:take])
                remaining -= take
        elif section["name"] in ("Key Files", "Archived Suggestions"):
            if remaining > 2000:
                full = section["text"]
                take = min(len(full), remaining)
                result_parts.append(full[:take])
                remaining -= take
        else:
            take = min(len(section["text"]), remaining)
            result_parts.append(section["text"][:take])
            remaining -= take
    return "\n".join(result_parts).strip()


def _iter_sections(context: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_name = "preamble"
    current_lines: list[str] = []
    for line in context.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections.append({"name": current_name, "text": "\n".join(current_lines)})
            current_name = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append({"name": current_name, "text": "\n".join(current_lines)})
    return sections
