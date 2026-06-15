from __future__ import annotations

import subprocess
from pathlib import Path


class RepoAnalysis:
    def __init__(self, name: str, clone_dir: Path) -> None:
        self.name = name
        self.clone_dir = clone_dir
        self.tech_stack: list[str] = []
        self.file_tree: str = ""
        self.total_files = 0
        self.total_lines = 0
        self.test_file_count = 0
        self.ci_files: list[str] = []
        self.lint_output: str = ""
        self.key_files: dict[str, str] = {}

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

    def build_file_tree(self, max_depth: int = 3) -> str:
        lines: list[str] = []
        clone = self.clone_dir
        for path in sorted(clone.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(clone)
            parts = rel.parts
            if any(p.startswith(".") and p not in (".github",) for p in parts):
                continue
            skip_dirs = {"__pycache__", "node_modules", "target", "build"}
            if any(p in skip_dirs for p in parts):
                continue
            if len(parts) > max_depth:
                continue
            self.total_files += 1
            try:
                line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
                self.total_lines += line_count
            except Exception:
                line_count = 0
            # Detect test files
            if "test" in parts[-1].lower() or "spec" in parts[-1].lower():
                self.test_file_count += 1
            indent = "  " * (len(parts) - 1)
            lines.append(f"{indent}{parts[-1]}  ({line_count} lines)")
        self.file_tree = "\n".join(lines[:200])
        return self.file_tree

    def read_key_files(self) -> None:
        targets = ["README.md", "CONTRIBUTING.md", ".gitignore", "docker-compose.yml",
                    ".github/workflows"]
        for name in targets:
            p = self.clone_dir / name
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    self.key_files[name] = content[:2000]
                except Exception:
                    pass
        # Build files
        for pattern in ["pom.xml", "build.gradle", "package.json", "pyproject.toml", "Cargo.toml"]:
            p = self.clone_dir / pattern
            if p.exists():
                try:
                    self.key_files[pattern] = p.read_text(encoding="utf-8", errors="ignore")[:2000]
                except Exception:
                    pass

    def run_linter(self, command: str | None) -> str:
        if not command:
            return "no linter configured"
        try:
            result = subprocess.run(
                command.split(), capture_output=True, text=True, cwd=self.clone_dir,
            )
            self.lint_output = (result.stdout + result.stderr)[:3000]
        except FileNotFoundError:
            self.lint_output = f"linter not found: {command}"
        return self.lint_output

    def detect_ci(self) -> None:
        workflows = self.clone_dir / ".github" / "workflows"
        if workflows.exists():
            def _rel(p):
                return str(p.relative_to(self.clone_dir))
            self.ci_files.extend(_rel(f) for f in workflows.glob("*.yml"))
            self.ci_files.extend(_rel(f) for f in workflows.glob("*.yaml"))
        for ci_file in [".travis.yml", ".gitlab-ci.yml", "Jenkinsfile"]:
            if (self.clone_dir / ci_file).exists():
                self.ci_files.append(ci_file)

    def to_context(self) -> str:
        parts = [
            f"# {self.name} - Codebase Analysis",
            f"Tech stack: {', '.join(self.tech_stack) or 'unknown'}",
            f"Total files: {self.total_files}, Total lines: {self.total_lines}",
            f"Test files found: {self.test_file_count}",
            f"CI files: {', '.join(self.ci_files) or 'none'}",
            "",
            "## File Tree",
            self.file_tree,
            "",
            "## Key Files",
        ]
        for name, content in self.key_files.items():
            parts.append(f"\n### {name}\n```\n{content}\n```")
        if self.lint_output:
            parts.append(f"\n## Lint Output\n```\n{self.lint_output}\n```")
        return "\n".join(parts)


def clone_or_pull(org: str, repo: str, dest: Path) -> Path:
    repo_path = dest / repo
    if repo_path.exists():
        subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_path, capture_output=True, check=False,
        )
    else:
        url = f"https://github.com/{org}/{repo}.git"
        subprocess.run(["git", "clone", url, str(repo_path)], capture_output=True, check=True)
    return repo_path
