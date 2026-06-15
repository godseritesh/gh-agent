from agent.pr import create_pr_body


def test_pr_body_contains_sections():
    body = create_pr_body({
        "problem": "Login fails",
        "change": "Fixed auth token handling",
        "testing": "Added unit tests",
        "risk": "Low",
    })
    assert "## Problem" in body
    assert "## Change" in body
    assert "## Testing" in body
    assert "## Risk" in body
    assert "Login fails" in body
    assert "Fixed auth token handling" in body


def test_pr_body_defaults_for_missing_keys():
    body = create_pr_body({})
    assert "No description" in body
    assert "No details" in body
    assert "No risk" not in body
    assert "Low" in body
    assert "Tests passed" in body
