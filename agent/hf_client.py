from __future__ import annotations

import re
import time
from typing import Any

import httpx

FREE_MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-2b-it",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
]

GROQ_FREE_MODELS = [
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

RATE_LIMIT_REMAINING_HEADER = "x-ratelimit-remaining"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

_PARAM_PATTERN = re.compile(r"(\d+\.?\d*)[bB]")
_CHAT_KW = frozenset(["instruct", "chat", "it", "dialog"])


class HFApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"HF API error {status}: {message}")


class HFRateLimitError(HFApiError):
    def __init__(self, message: str) -> None:
        super().__init__(429, message)


class GroqApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"Groq API error {status}: {message}")


class HFClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = "https://router.huggingface.co/v1/chat/completions",
        timeout: float = DEFAULT_TIMEOUT,
        hf_token: str | None = None,
        groq_api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        token = token or hf_token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(headers=headers, timeout=timeout)
        self._groq_key = groq_api_key
        if groq_api_key:
            self._groq_client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
        else:
            self._groq_client = None

    def close(self) -> None:
        self._client.close()
        if self._groq_client:
            self._groq_client.close()

    def _call_groq(self, model: str, prompt: str, **kwargs: Any) -> str:
        if not self._groq_client:
            raise GroqApiError(0, "No Groq API key configured")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        resp = self._groq_client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload
        )
        if resp.status_code != 200:
            raise GroqApiError(resp.status_code, resp.text[:200])
        result = resp.json()
        content = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return content.strip()

    def _call_model(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self._client.post(self.base_url, json=payload)
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
        # 1. Try Groq first (free, fast, reliable)
        if self._groq_client:
            for model in GROQ_FREE_MODELS:
                try:
                    return self._call_groq(model, prompt, **kwargs)
                except GroqApiError:
                    continue

        # 2. Dynamic discovery from HF Hub
        models = self._discover_free_models()
        for m in FREE_MODELS:
            if m not in models:
                models.append(m)

        # 3. Try HF router
        errors: list[Exception] = []
        for model in models:
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
