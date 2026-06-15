from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent.state import AgentState

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_empty_state(tmp_path):
    state = AgentState.load(tmp_path / "nonexistent.json")
    assert state.last_checked_commit == {}
    assert state.in_progress is None


def test_load_corrupt_state():
    with pytest.raises(ValueError, match="Corrupt"):
        AgentState.load(FIXTURES / "corrupt_state.json")


def test_load_valid_state():
    state = AgentState.load(FIXTURES / "valid_state.json")
    assert state.get_last_commit("SkyLink") == "abc123"
    assert state.token_budget["tokens_used"] == 5000


def test_save_and_reload(tmp_path):
    state = AgentState()
    state.set_last_commit("TestRepo", "xyz789")
    state.start_task("test-task")
    path = tmp_path / "state.json"
    state.save(path)
    loaded = AgentState.load(path)
    assert loaded.get_last_commit("TestRepo") == "xyz789"
    assert loaded.in_progress == "test-task"


def test_start_task_when_busy():
    state = AgentState({"in_progress": "existing"})
    with pytest.raises(RuntimeError, match="already in progress"):
        state.start_task("new-task")


def test_finish_task():
    state = AgentState({"in_progress": "task-1"})
    state.finish_task()
    assert state.in_progress is None


def test_token_budget_within_limit():
    state = AgentState()
    assert state.can_use_tokens(100) is True


def test_token_budget_exceeded():
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    state = AgentState({
        "token_budget": {"date": today, "tokens_used": 29000, "daily_limit": 30000}
    })
    assert state.can_use_tokens(2000) is False
    assert state.can_use_tokens(500) is True


def test_token_budget_resets_daily():
    state = AgentState({
        "token_budget": {"date": "2000-01-01", "tokens_used": 29000, "daily_limit": 30000}
    })
    assert state.can_use_tokens(5000) is True
    state.record_tokens(5000)
    assert state.token_budget["tokens_used"] == 5000
