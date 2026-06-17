from __future__ import annotations

import time
from typing import Any

import httpx

FREE_MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-2b-it",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
]

RATE_LIMIT_REMAINING_HEADER = "x-ratelimit-remaining"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


class HFApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"HF API error {status}: {message}")


class HFRateLimitError(HFApiError):
    def __init__(self, message: str) -> None:
        super().__init__(429, message)


class HFClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = "https://api-inference.huggingface.co",
        timeout: float = DEFAULT_TIMEOUT,
        hf_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        token = token or hf_token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def _call_model(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}/models/{model}/v1/chat/completions"
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self._client.post(url, json=payload)
            if resp.status_code == 429:
                remaining = resp.headers.get(RATE_LIMIT_REMAINING_HEADER, "0")
                if attempt < MAX_RETRIES and int(remaining) < 100:
                    sleep = RETRY_BACKOFF ** attempt
                    time.sleep(sleep)
                    continue
                raise HFRateLimitError(resp.text[:200])
            if resp.status_code != 200:
                raise HFApiError(resp.status_code, resp.text[:200])
            return resp.json()
        raise HFRateLimitError("Exhausted retries")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        errors: list[Exception] = []
        for model in FREE_MODELS:
            try:
                result = self._call_model(model, prompt, **kwargs)
                content = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return content.strip()
            except (HFRateLimitError, HFApiError) as e:
                errors.append(e)
                continue
        raise HFApiError(0, f"All models failed: {'; '.join(str(e) for e in errors)}")
