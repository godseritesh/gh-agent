from pathlib import Path

from agent.planner import analyze_repo, create_plan, pick_best_suggestion
from agent.scanner import RepoAnalysis


def test_analyze_repo_success():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            data = ('[{"title": "Add tests", "category": "test", '
                    '"impact": "high", "effort": "small", "rationale": "missing"}]')
            return data

    analysis = RepoAnalysis("Test", Path("/tmp"))
    result = analyze_repo(FakeClient(), analysis)
    assert len(result) == 1
    assert result[0]["title"] == "Add tests"


def test_analyze_repo_parse_fallback():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return "broken json"

    analysis = RepoAnalysis("Test", Path("/tmp"))
    result = analyze_repo(FakeClient(), analysis)
    assert result == []


def test_pick_best_suggestion_prefers_high_impact():
    suggestions = [
        {"title": "Low", "impact": "low", "effort": "small"},
        {"title": "High", "impact": "high", "effort": "small"},
        {"title": "Medium", "impact": "medium", "effort": "small"},
    ]
    best = pick_best_suggestion(suggestions, max_effort="medium")
    assert best["title"] == "High"


def test_pick_best_suggestion_filters_by_effort():
    suggestions = [
        {"title": "Large", "impact": "high", "effort": "large"},
        {"title": "Small", "impact": "medium", "effort": "small"},
    ]
    best = pick_best_suggestion(suggestions, max_effort="small")
    assert best["title"] == "Small"


def test_pick_best_suggestion_empty():
    assert pick_best_suggestion([]) is None


def test_pick_best_suggestion_none_fit():
    suggestions = [{"title": "Big", "impact": "high", "effort": "large"}]
    assert pick_best_suggestion(suggestions, max_effort="small") is None


def test_create_plan_success():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return '[{"step": "fix auth", "verify": "tests pass", "files": ["auth.py"]}]'

    result = create_plan(
        FakeClient(), "SkyLink", {"title": "fix login", "files_likely_involved": ["auth.py"]},
    )
    assert len(result) == 1
    assert result[0]["step"] == "fix auth"


def test_create_plan_parse_fallback():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return "broken"

    result = create_plan(
        FakeClient(), "SkyLink", {"title": "fix", "files_likely_involved": ["f.py"]},
    )
    assert result == []
