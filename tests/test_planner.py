from agent.planner import classify_issue, create_plan


def test_classify_issue_success():
    calls = []

    class FakeClient:
        def generate(self, prompt, **kwargs):
            calls.append(prompt)
            data = '{"priority": "high", "category": "bug", '
            data += '"impact": "users cannot login", "explanation": "auth broken"}'
            return data

    result = classify_issue(FakeClient(), "login bug")
    assert result["priority"] == "high"
    assert result["category"] == "bug"
    assert len(calls) == 1


def test_classify_issue_parse_fallback():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return "not valid json at all"

    result = classify_issue(FakeClient(), "test")
    assert result["priority"] == "medium"
    assert result["category"] == "bug"


def test_create_plan_success():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return '[{"step": "fix auth", "verify": "tests pass", "files": ["auth.py"]}]'

    result = create_plan(FakeClient(), "SkyLink", "fix login", ["auth.py"])
    assert len(result) == 1
    assert result[0]["step"] == "fix auth"


def test_create_plan_parse_fallback():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            return "broken"

    result = create_plan(FakeClient(), "SkyLink", "fix", ["f.py"])
    assert result == []
