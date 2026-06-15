from __future__ import annotations

from agent.hf_client import HFClient

PRIORITY_PROMPT = """You are a code reviewer for the godseritesh GitHub organization.
Classify the following issue or code change. Respond with ONLY a JSON object.

Issue/Change: {description}

{{
  "priority": "high" | "medium" | "low",
  "category": "bug" | "feature" | "refactor" | "docs" | "security",
  "impact": "The business or user-facing impact of this change",
  "explanation": "One-sentence justification"
}}"""

PLAN_PROMPT = """You are an engineer planning a code change. Produce a minimal plan.

Task: {description}
Repository: {repo}
Changed files: {files}

Respond with a JSON array of tasks:
[
  {{
    "step": "description of what to do",
    "verify": "how to verify this step succeeded",
    "files": ["list of files to modify"]
  }}
]

Limit to 3 subtasks. Keep each step concrete and minimal."""


def classify_issue(client: HFClient, description: str) -> dict:
    prompt = PRIORITY_PROMPT.format(description=description)
    result = client.generate(prompt, parameters={"max_new_tokens": 200})
    import json
    try:
        cleaned = result.strip()
        for prefix in ["```json", "```"]:
            cleaned = cleaned.removeprefix(prefix)
        cleaned = cleaned.removesuffix("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"priority": "medium", "category": "bug", "impact": "unknown",
                "explanation": "parse failed"}


def create_plan(client: HFClient, repo: str, description: str, files: list[str]) -> list[dict]:
    files_str = "\n".join(files)
    prompt = PLAN_PROMPT.format(repo=repo, description=description, files=files_str)
    result = client.generate(prompt, parameters={"max_new_tokens": 500})
    import json
    try:
        cleaned = result.strip()
        for prefix in ["```json", "```"]:
            cleaned = cleaned.removeprefix(prefix)
        cleaned = cleaned.removesuffix("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return []
