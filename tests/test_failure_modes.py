from pathlib import Path

import pytest

from agent.config import AgentConfig
from agent.hf_client import HFApiError, HFClient
from agent.state import AgentState

FIXTURES = Path(__file__).parent / "fixtures"


def test_corrupt_state_file():
    with pytest.raises(ValueError, match="Corrupt"):
        AgentState.load(FIXTURES / "corrupt_state.json")


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        AgentConfig.load("/nonexistent/path/config.yaml")


def test_api_500_error():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []

    def mock_call(model, prompt, **kwargs):
        raise HFApiError(500, "Internal Server Error")

    client._call_model = mock_call
    with pytest.raises(HFApiError, match="500"):
        client.generate("test")


def test_api_timeout_is_error():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []

    def mock_call(model, prompt, **kwargs):
        raise HFApiError(0, "timeout")

    client._call_model = mock_call
    with pytest.raises(HFApiError):
        client.generate("test")


def test_fail_to_start_task_when_busy():
    state = AgentState({"in_progress": "busy"})
    with pytest.raises(RuntimeError, match="already in progress"):
        state.start_task("new-one")


def test_token_budget_daily_reset():
    state = AgentState({
        "token_budget": {"date": "2020-01-01", "tokens_used": 30000, "daily_limit": 30000}
    })
    assert state.can_use_tokens(100) is True, "Should reset on new day"


def test_invalid_config_yaml(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("repos:\n  BadRepo:\n    active: not_a_bool\n", encoding="utf-8")
    cfg = AgentConfig.load(f)
    assert cfg.repos["BadRepo"].active is True  # non-bool treated as True
