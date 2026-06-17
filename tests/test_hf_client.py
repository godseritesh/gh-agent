import pytest

from agent.hf_client import FREE_MODELS, HFApiError, HFClient, HFRateLimitError


def test_generate_successful_response():
    client = HFClient("fake-token")
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

    def mock_call(model, prompt, **kwargs):
        raise HFApiError(500, "internal error")

    client._call_model = mock_call
    with pytest.raises(HFApiError, match="All models failed"):
        client.generate("test prompt")


def test_rate_limit_exhausts_retries():
    client = HFClient("fake-token")
    call_count = 0

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        raise HFRateLimitError("rate limited")

    client._call_model = mock_call
    with pytest.raises(HFApiError, match="All models failed"):
        client.generate("test prompt")
    assert call_count == len(FREE_MODELS)


def test_chat_completions_url():
    client = HFClient("fake-token")
    assert "api-inference.huggingface.co" in client.base_url

def test_model_specific_url():
    client = HFClient("fake-token")
    captured = {}

    def mock_post(url, json, **kwargs):
        captured["url"] = url
        from unittest.mock import Mock
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        return resp

    client._client.post = mock_post
    client.generate("hi")
    assert "models/Qwen/Qwen2.5-7B-Instruct/v1/chat/completions" in captured["url"]
