import pytest

from agent.hf_client import (
    FREE_MODELS,
    GROQ_FREE_MODELS,
    GroqApiError,
    HFApiError,
    HFClient,
    HFRateLimitError,
)


def test_generate_successful_response():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []
    call_count = 0
    captured = {}

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count, captured
        call_count += 1
        captured["model"] = model
        captured["prompt"] = prompt
        return {"choices": [{"message": {"content": "the answer"}}]}

    client._call_model = mock_call
    result = client.generate("test prompt")
    assert result == "the answer"
    assert call_count == 1
    assert captured["model"] == FREE_MODELS[0]
    assert captured["prompt"] == "test prompt"


def test_fallback_on_rate_limit():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []
    call_count = 0

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise HFRateLimitError("rate limited")
        return {"choices": [{"message": {"content": "fallback result"}}]}

    client._call_model = mock_call
    result = client.generate("test prompt")
    assert result == "fallback result"
    assert call_count == 2


def test_all_models_fail():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []

    def mock_call(model, prompt, **kwargs):
        raise HFApiError(500, "internal error")

    client._call_model = mock_call
    with pytest.raises(HFApiError, match="All models failed"):
        client.generate("test prompt")


def test_rate_limit_exhausts_retries():
    client = HFClient("fake-token")
    client._discover_free_models = lambda max_count=5: []
    call_count = 0

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        raise HFRateLimitError("rate limited")

    client._call_model = mock_call
    with pytest.raises(HFApiError, match="All models failed"):
        client.generate("test prompt")
    assert call_count == len(FREE_MODELS)


def test_groq_used_when_key_provided():
    client = HFClient("fake-token", groq_api_key="gsk-test")
    called = []
    client._call_groq = lambda model, prompt, **kwargs: (
        called.append(model) or "groq reply"
    )
    result = client.generate("test")
    assert result == "groq reply"
    assert called[0] == GROQ_FREE_MODELS[0]


def test_groq_skipped_when_no_key():
    client = HFClient("fake-token")
    client._call_groq = lambda model, prompt, **kwargs: (_ for _ in ()).throw(
        GroqApiError(0, "should not be called")
    )
    client._discover_free_models = lambda max_count=5: []

    def mock_call(model, prompt, **kwargs):
        return {"choices": [{"message": {"content": "hf reply"}}]}

    client._call_model = mock_call
    result = client.generate("test")
    assert result == "hf reply"


def test_groq_fallback_on_error():
    client = HFClient("fake-token", groq_api_key="gsk-test")
    groq_call_count = 0

    def mock_groq(model, prompt, **kwargs):
        nonlocal groq_call_count
        groq_call_count += 1
        raise GroqApiError(500, "groq error")

    client._call_groq = mock_groq
    client._discover_free_models = lambda max_count=5: []

    def mock_call(model, prompt, **kwargs):
        return {"choices": [{"message": {"content": "hf fallback"}}]}

    client._call_model = mock_call
    result = client.generate("test")
    assert result == "hf fallback"
    assert groq_call_count == len(GROQ_FREE_MODELS)


def test_router_url():
    client = HFClient("fake-token")
    assert "router.huggingface.co" in client.base_url
