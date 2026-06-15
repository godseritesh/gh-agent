from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class RepoInfo:
    def __init__(self, name: str, clone_dir: Path) -> None:
        self.name = name
        self.clone_dir = clone_dir
        self.ci_files: list[str] = []
        self.tech_stack: list[str] = []
        self.issues: list[dict[str, Any]] = []

    def detect_ci(self) -> None:
        workflows = self.clone_dir / ".github" / "workflows"
        if workflows.exists():
            rel = self.clone_dir
            self.ci_files.extend(str(f.relative_to(rel)) for f in workflows.glob("*.yml"))
            self.ci_files.extend(str(f.relative_to(rel)) for f in workflows.glob("*.yaml"))
        for ci_file in [".travis.yml", ".gitlab-ci.yml", "Jenkinsfile"]:
            if (self.clone_dir / ci_file).exists():
                self.ci_files.append(ci_file)

    def detect_stack(self) -> None:
        indicators: list[tuple[list[str], str]] = [
            (["pom.xml", "build.gradle"], "Java"),
            (["package.json"], "Node.js"),
            (["requirements.txt", "setup.py", "pyproject.toml"], "Python"),
            (["Cargo.toml"], "Rust"),
            (["go.mod"], "Go"),
            (["Gemfile"], "Ruby"),
        ]
        for files, stack in indicators:
            if any((self.clone_dir / f).exists() for f in files):
                self.tech_stack.append(stack)

    def get_changed_files(self, base_commit: str | None) -> list[str]:
        if not base_commit:
            return []
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_commit}..HEAD"],
                capture_output=True, text=True, check=True, cwd=self.clone_dir,
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            return []


def clone_or_pull(org: str, repo: str, dest: Path) -> Path:
    repo_path = dest / repo
    if repo_path.exists():
        subprocess.run(["git", "pull"], cwd=repo_path, capture_output=True, check=True)
    else:
        url = f"https://github.com/{org}/{repo}.git"
        subprocess.run(["git", "clone", url, str(repo_path)], capture_output=True, check=True)
    return repo_path


def scan_repo(repo_info: RepoInfo, base_commit: str | None) -> list[dict[str, Any]]:
    repo_info.detect_ci()
    repo_info.detect_stack()
    changed = repo_info.get_changed_files(base_commit)
    return changed
