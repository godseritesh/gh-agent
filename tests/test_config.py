from pathlib import Path

import pytest

from agent.config import AgentConfig, RepoConfig

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_config():
    cfg = AgentConfig.load(FIXTURES / "valid_config.yaml")
    assert "SkyLink" in cfg.repos
    assert "OptiHeart_Retinal_Insight_to_Cardiac_Health" in cfg.repos
    assert cfg.repos["SkyLink"].test_framework == "junit"
    assert cfg.repos["SkyLink"].active is True
    assert cfg.repos["SkyLink"].has_tests is True


def test_load_missing_file():
    with pytest.raises(FileNotFoundError):
        AgentConfig.load("nonexistent.yaml")


def test_load_empty_config(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("repos: {}", encoding="utf-8")
    cfg = AgentConfig.load(f)
    assert cfg.repos == {}


def test_repo_config_defaults():
    rc = RepoConfig({})
    assert rc.test_framework is None
    assert rc.active is True
    assert rc.has_tests is False


def test_active_repos_filter():
    cfg = AgentConfig({"repos": {"A": {"active": True}, "B": {"active": False}}})
    assert cfg.active_repos == ["A"]


def test_get_missing_repo():
    cfg = AgentConfig({"repos": {}})
    assert cfg.get("nonexistent") is None
