from agent.coder import apply_patch, implement_step


def test_implement_step_prompt_format():
    class FakeClient:
        def generate(self, prompt, **kwargs):
            assert "def hello(): pass" in prompt
            assert "SkyLink" in prompt
            assert "fix" in prompt
            return "def hello():\n    return 'fixed'"

    code = "def hello(): pass"
    result = implement_step(FakeClient(), "SkyLink", "fix the bug", "src/main.py", code, "python")
    assert result == "def hello():\n    return 'fixed'"


def test_apply_patch(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("old", encoding="utf-8")
    apply_patch(f, "new content")
    assert f.read_text(encoding="utf-8") == "new content"
