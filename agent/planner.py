from __future__ import annotations

import json

from agent.hf_client import HFClient
from agent.scanner import RepoAnalysis

REVIEW_PROMPT = """You are an senior engineer reviewing a codebase. Analyze this repo and suggest
improvements. Focus on: missing tests, error handling gaps, security issues, performance problems,
code smells, and feature gaps.

{context}

Respond with ONLY a JSON array of suggestions. Max 5 suggestions.
Each suggestion:
{{
  "title": "short title",
  "category": "bug" | "test" | "refactor" | "feature" | "docs" | "security",
  "impact": "high" | "medium" | "low",
  "effort": "small" | "medium" | "large",
  "rationale": "why this matters (1 sentence)",
  "files_likely_involved": ["file1", "file2"]
}}

If you cannot identify any genuine improvements, respond with empty array []."""

PLAN_PROMPT = """You are implementing a change in {repo}. Given the suggestion below, produce
a minimal implementation plan.

Suggestion: {suggestion}

Relevant files: {files}

Respond with a JSON array of steps:
[
  {{
    "step": "concrete action",
    "verify": "how to verify this step",
    "files": ["file paths to modify"]
  }}
]

Max 3 steps. Each step must be concrete (specific function/class to change)."""

REVIEW_COMMAND_PROMPT = """Given this suggestion and repo context, output a single bash command
that would help verify or understand the area of code involved. Output ONLY the command, no
explanations.

Suggestion: {suggestion}
Context: {context}

If the suggestion involves a specific language/tool, output the appropriate command
(e.g. 'grep -r "TODO" src/', 'ruff check src/', 'find src -name "*.py" | head -20')."""


def analyze_repo(client: HFClient, analysis: RepoAnalysis) -> list[dict]:
    """Send full repo analysis to LLM and get back improvement suggestions."""
    context = analysis.to_context()
    prompt = REVIEW_PROMPT.format(context=context[:12000])
    result = client.generate(prompt, parameters={"max_new_tokens": 1000})
    try:
        cleaned = result.strip()
        for prefix in ["```json", "```"]:
            cleaned = cleaned.removeprefix(prefix)
        cleaned = cleaned.removesuffix("```").strip()
        suggestions = json.loads(cleaned)
        if isinstance(suggestions, dict) and "suggestions" in suggestions:
            suggestions = suggestions["suggestions"]
        return suggestions if isinstance(suggestions, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def pick_best_suggestion(suggestions: list[dict], max_effort: str = "medium") -> dict | None:
    """Pick highest-impact suggestion that fits within effort budget."""
    if not suggestions:
        return None
    scored = []
    impact_map = {"high": 3, "medium": 2, "low": 1}
    effort_map = {"small": 1, "medium": 2, "large": 3}
    max_effort_val = effort_map.get(max_effort, 2)
    for s in suggestions:
        effort = s.get("effort", "medium")
        s_effort_val = effort_map.get(effort, 2)
        if s_effort_val > max_effort_val:
            continue
        impact = impact_map.get(s.get("impact", "low"), 1)
        scored.append((impact, s_effort_val, s))
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


def create_plan(client: HFClient, repo: str, suggestion: dict) -> list[dict]:
    """Create a step-by-step implementation plan for a suggestion."""
    files = suggestion.get("files_likely_involved", [])
    prompt = PLAN_PROMPT.format(repo=repo, suggestion=suggestion["title"], files=", ".join(files))
    result = client.generate(prompt, parameters={"max_new_tokens": 500})
    try:
        cleaned = result.strip()
        for prefix in ["```json", "```"]:
            cleaned = cleaned.removeprefix(prefix)
        cleaned = cleaned.removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return []


def get_verify_command(client: HFClient, suggestion: dict, context: str) -> str | None:
    """Ask LLM for a shell command to verify the area of code."""
    prompt = REVIEW_COMMAND_PROMPT.format(suggestion=suggestion["title"], context=context[:2000])
    try:
        result = client.generate(prompt, parameters={"max_new_tokens": 100})
        return result.strip()
    except Exception:
        return None
