from pathlib import Path

from agent import agents_md
from agent.scanner import RepoAnalysis


def test_filename():
    assert agents_md.filename("SkyLink") == "AGENTS-SkyLink.md"


def test_generate_initial_context():
    analysis = RepoAnalysis("TestRepo", Path("/tmp"))
    analysis.tech_stack = ["Python", "FastAPI"]
    analysis.total_files = 42
    analysis.total_lines = 5000
    analysis.test_file_count = 5
    analysis.ci_files = [".github/workflows/test.yml"]

    context = agents_md.generate_initial_context("TestRepo", analysis, [])
    assert "TestRepo" in context
    assert "Agent Knowledge Base" in context
    assert "Python, FastAPI" in context
    assert "42" in context
    assert "5000" in context
    assert "5" in context


def test_generate_with_suggestions():
    analysis = RepoAnalysis("R", Path("/tmp"))
    suggestions = [
        {"title": "Add CI", "impact": "high", "effort": "small", "rationale": "No CI pipeline"}
    ]
    context = agents_md.generate_initial_context("R", analysis, suggestions)
    assert "Add CI" in context
    assert "[high]" in context
    assert "No CI pipeline" in context


def test_append_shipped_entry():
    analysis = RepoAnalysis("R", Path("/tmp"))
    context = agents_md.generate_initial_context("R", analysis, [])
    entry = {
        "title": "Added CI pipeline",
        "category": "feature",
        "impact": "high",
        "rationale": "Repo lacked automated testing",
        "pr_url": "https://github.com/org/repo/pull/1",
    }
    updated = agents_md.append_shipped_entry(context, entry)
    assert "Added CI pipeline" in updated
    assert "feature" in updated
    assert "https://github.com/org/repo/pull/1" in updated


def test_save_and_load(tmp_path):
    context = "# Test Knowledge Base\n\nSome context here"
    path = tmp_path / "AGENTS-Test.md"
    agents_md.save(context, path)
    loaded = agents_md.load(path)
    assert loaded == context


def test_load_nonexistent(tmp_path):
    loaded = agents_md.load(tmp_path / "AGENTS-Nonexistent.md")
    assert loaded == ""


def test_get_context_for_llm():
    context = "A" * 1000
    result = agents_md.get_context_for_llm(context, max_chars=100)
    assert len(result) == 100
