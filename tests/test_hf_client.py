import pytest

from agent.hf_client import FREE_MODELS, HFApiError, HFClient, HFRateLimitError


def test_generate_successful_response():
    client = HFClient("fake-token")
    call_count = 0

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        assert model == FREE_MODELS[0]
        return [{"generated_text": "test prompt the answer"}]

    client._call_model = mock_call
    result = client.generate("test prompt")
    assert result == "the answer"
    assert call_count == 1


def test_fallback_on_rate_limit():
    client = HFClient("fake-token")
    call_count = 0

    def mock_call(model, prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise HFRateLimitError("rate limited")
        return [{"generated_text": "test prompt fallback result"}]

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
