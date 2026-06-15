from pathlib import Path
from typing import Any

import yaml


class RepoConfig:
    def __init__(self, data: dict[str, Any]) -> None:
        self.test_framework: str | None = data.get("test_framework")
        self.build_command: str | None = data.get("build_command")
        self.lint_command: str | None = data.get("lint_command")
        self.deploy_command: str | None = data.get("deploy_command")
        active_raw = data.get("active", True)
        self.active: bool = bool(active_raw) if isinstance(active_raw, bool) else True

    @property
    def has_tests(self) -> bool:
        return self.test_framework is not None


class AgentConfig:
    SCHEMA = {"repos": dict}

    def __init__(self, data: dict[str, Any]) -> None:
        self.repos: dict[str, RepoConfig] = {}
        for name, cfg in data.get("repos", {}).items():
            self.repos[name] = RepoConfig(cfg) if isinstance(cfg, dict) else RepoConfig({})

    @classmethod
    def load(cls, path: str | Path) -> "AgentConfig":
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("Config must be a YAML mapping")
        return cls(data)

    def get(self, repo_name: str) -> RepoConfig | None:
        return self.repos.get(repo_name)

    @property
    def active_repos(self) -> list[str]:
        return [name for name, cfg in self.repos.items() if cfg.active]
