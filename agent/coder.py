from __future__ import annotations

import subprocess
from pathlib import Path

from agent.hf_client import HFClient

FIX_PROMPT = """You are fixing a bug in the {repo} repository.

Problem: {description}
File: {filepath}
Current code:
```{language}
{code}
```

Produce ONLY the corrected code. No explanations, no markdown fences."""


def generate_fix(
    client: HFClient,
    repo: str,
    description: str,
    filepath: str,
    code: str,
    language: str = "python",
) -> str:
    prompt = FIX_PROMPT.format(
        repo=repo, description=description, filepath=filepath, language=language, code=code,
    )
    return client.generate(prompt, parameters={"max_new_tokens": 1024})


def apply_patch(filepath: Path, new_content: str) -> None:
    filepath.write_text(new_content, encoding="utf-8")


def run_tests(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "no test command configured")
    result = subprocess.run(
        command.split(),
        capture_output=True, text=True, cwd=repo_dir,
    )
    return (result.returncode, result.stdout + result.stderr)


def run_linter(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "no lint command configured")
    result = subprocess.run(
        command.split(),
        capture_output=True, text=True, cwd=repo_dir,
    )
    return (result.returncode, result.stdout + result.stderr)
