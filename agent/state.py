from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AgentState:
    FILE_NAME = "agent-state.json"

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        data = data or {}
        self.last_checked_commit: dict[str, str] = data.get("last_checked_commit", {})
        self.in_progress: str | None = data.get("in_progress")
        self.token_budget: dict[str, Any] = data.get("token_budget", self._default_budget())

    @staticmethod
    def _default_budget() -> dict[str, Any]:
        return {
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "tokens_used": 0,
            "daily_limit": 30000,
        }

    @classmethod
    def load(cls, path: str | Path) -> AgentState:
        p = Path(path)
        if not p.exists():
            return cls()
        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupt state file: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("State file must contain a JSON object")
        return cls(data)

    def save(self, path: str | Path) -> None:
        data = {
            "last_checked_commit": self.last_checked_commit,
            "in_progress": self.in_progress,
            "token_budget": self.token_budget,
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_last_commit(self, repo: str) -> str | None:
        return self.last_checked_commit.get(repo)

    def set_last_commit(self, repo: str, commit: str) -> None:
        self.last_checked_commit[repo] = commit

    def start_task(self, task_id: str) -> None:
        if self.in_progress is not None:
            raise RuntimeError(f"Cannot start {task_id}: {self.in_progress} already in progress")
        self.in_progress = task_id

    def finish_task(self) -> None:
        self.in_progress = None

    def can_use_tokens(self, tokens: int) -> bool:
        budget = self.token_budget
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if budget["date"] != today:
            budget["date"] = today
            budget["tokens_used"] = 0
        return budget["tokens_used"] + tokens <= budget["daily_limit"]

    def record_tokens(self, tokens: int) -> None:
        budget = self.token_budget
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if budget["date"] != today:
            budget["date"] = today
            budget["tokens_used"] = 0
        budget["tokens_used"] += tokens
