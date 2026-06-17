from __future__ import annotations

import re
import subprocess
from pathlib import Path

from agent.hf_client import HFClient


def strip_fences(text: str) -> str:
    """Remove markdown code fences from generated code."""
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


IMPLEMENT_PROMPT = """You are implementing a change in {repo}.

Step: {step}
File: {filepath}

Project build file (only these dependencies are available):
```{language}
{build_context}
```

Current code:
```{language}
{code}
```

RULES:
- Do NOT add any new imports. Only use imports already in the code or build file.
- Do NOT change project structure (packages, directory layout, framework).
- Make ONLY the minimal change described in the step. No unrelated changes.
- Preserve existing style exactly.

Output ONLY the complete new file content. No explanations, no markdown fences."""

TEST_PROMPT = """You are writing a test for {repo}.

Production code to test:
```{language}
{code}
```

Write a test for this code. Follow the existing test style in the project.
Output ONLY the test code. No explanations, no markdown fences."""


def implement_step(
    client: HFClient,
    repo: str,
    step: str,
    filepath: str,
    code: str,
    language: str = "python",
    build_context: str = "",
) -> str:
    prompt = IMPLEMENT_PROMPT.format(
        repo=repo, step=step, filepath=filepath, language=language,
        code=code, build_context=build_context or "(none)",
    )
    result = client.generate(prompt, parameters={"max_new_tokens": 1500})
    return strip_fences(result)


def generate_test(
    client: HFClient,
    repo: str,
    code: str,
    language: str = "python",
) -> str:
    prompt = TEST_PROMPT.format(repo=repo, language=language, code=code)
    result = client.generate(prompt, parameters={"max_new_tokens": 1000})
    return strip_fences(result)


def apply_patch(filepath: Path, new_content: str) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(new_content, encoding="utf-8")


def run_tests(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "")
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, cwd=repo_dir, timeout=120,
        )
        return (result.returncode, result.stdout + result.stderr)
    except FileNotFoundError:
        return (0, f"test binary not found: {command}")
    except subprocess.TimeoutExpired:
        return (0, "test timed out")


def run_linter(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "no lint command configured")
    result = subprocess.run(
        command.split(), capture_output=True, text=True, cwd=repo_dir,
    )
    return (result.returncode, result.stdout + result.stderr)
