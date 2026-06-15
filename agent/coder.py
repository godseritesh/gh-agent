from __future__ import annotations

import subprocess
from pathlib import Path

from agent.hf_client import HFClient

IMPLEMENT_PROMPT = """You are implementing a change in {repo}.

Step: {step}
File: {filepath}
Current code:
```{language}
{code}
```

Implement the change described in the step. Preserve existing style.
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
) -> str:
    prompt = IMPLEMENT_PROMPT.format(
        repo=repo, step=step, filepath=filepath, language=language, code=code,
    )
    return client.generate(prompt, parameters={"max_new_tokens": 1500})


def generate_test(
    client: HFClient,
    repo: str,
    code: str,
    language: str = "python",
) -> str:
    prompt = TEST_PROMPT.format(repo=repo, language=language, code=code)
    return client.generate(prompt, parameters={"max_new_tokens": 1000})


def apply_patch(filepath: Path, new_content: str) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(new_content, encoding="utf-8")


def run_tests(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "no test command configured")
    result = subprocess.run(
        command.split(), capture_output=True, text=True, cwd=repo_dir,
    )
    return (result.returncode, result.stdout + result.stderr)


def run_linter(repo_dir: Path, command: str | None) -> tuple[int, str]:
    if not command:
        return (0, "no lint command configured")
    result = subprocess.run(
        command.split(), capture_output=True, text=True, cwd=repo_dir,
    )
    return (result.returncode, result.stdout + result.stderr)
