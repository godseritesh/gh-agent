from __future__ import annotations

import time
from typing import Any

import httpx

# Max models the agent will try in order of preference.
# If primary is rate-limited or unavailable, fallback to next.
FREE_MODELS = [
    "Qwen/Qwen3-27B",      # primary — Apache 2.0, strong coding
    "google/gemma-4-4b",   # fallback 1 — Apache 2.0, fast
    "microsoft/phi-4",     # fallback 2 — MIT, small reasoning
]

RATE_LIMIT_REMAINING_HEADER = "x-ratelimit-remaining"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds, doubles each retry


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
        base_url: str = "https://router.huggingface.co/hf-inference/models",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def _call_model(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}/{model}"
        payload = {"inputs": prompt, **kwargs}
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
                if isinstance(result, list) and len(result) > 0:
                    generated = result[0].get("generated_text", "")
                    return generated[len(prompt):].strip()
                if isinstance(result, dict):
                    return result.get("generated_text", "").strip()
            except (HFRateLimitError, HFApiError) as e:
                errors.append(e)
                continue
        raise HFApiError(0, f"All models failed: {'; '.join(str(e) for e in errors)}")
