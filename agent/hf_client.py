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
    "llama-3.3-70b-specdec",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

GITHUB_MODELS_MODELS = ["gpt-4o-mini"]
GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

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


class GithubModelsApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"GitHub Models API error {status}: {message}")


class GeminiApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"Gemini API error {status}: {message}")


class HFClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = "https://router.huggingface.co/v1/chat/completions",
        timeout: float = DEFAULT_TIMEOUT,
        hf_token: str | None = None,
        groq_api_key: str | None = None,
        gh_token: str | None = None,
        gemini_api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        token = token or hf_token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(headers=headers, timeout=timeout)
        self._groq_key = groq_api_key
        self._last_groq_call: float = 0.0
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
        if gh_token:
            self._gh_client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {gh_token}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
        else:
            self._gh_client = None
        self._gemini_key = gemini_api_key
        self._gemini_client = (
            httpx.Client(timeout=timeout) if gemini_api_key else None
        )

    def close(self) -> None:
        self._client.close()
        if self._groq_client:
            self._groq_client.close()
        if self._gh_client:
            self._gh_client.close()
        if self._gemini_client:
            self._gemini_client.close()

    def _discover_free_models(self, max_count: int = 5) -> list[str]:
        """Query HF Hub for popular free chat models under ~10B params."""
        try:
            resp = self._client.get(
                "https://huggingface.co/api/models",
                params={
                    "pipeline_tag": "text-generation",
                    "sort": "downloads",
                    "direction": -1,
                    "limit": 50,
                },
                timeout=10.0,
            )
            if resp.status_code != 200:
                return []
            models = resp.json()
        except Exception:
            return []

        discovered: list[str] = []
        for model in models:
            model_id: str = model.get("id", "")
            lid = model_id.lower()
            if not any(kw in lid for kw in _CHAT_KW):
                continue
            m = _PARAM_PATTERN.search(lid)
            if m and float(m.group(1)) > 10:
                continue
            discovered.append(model_id)
            if len(discovered) >= max_count:
                break
        return discovered

    def _call_groq(self, model: str, prompt: str, **kwargs: Any) -> str:
        if not self._groq_client:
            raise GroqApiError(0, "No Groq API key configured")
        # Enforce 2s minimum between Groq calls (30 RPM limit)
        elapsed = time.monotonic() - self._last_groq_call
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        # Groq uses OpenAI-compatible API — convert HuggingFace-specific parameters
        params = kwargs.pop("parameters", {})
        if isinstance(params, dict):
            if "max_new_tokens" in params:
                kwargs["max_tokens"] = params["max_new_tokens"]
            if "temperature" in params:
                kwargs["temperature"] = params["temperature"]
        groq_kwargs = kwargs
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **groq_kwargs,
        }
        resp = self._groq_client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload
        )
        self._last_groq_call = time.monotonic()
        if resp.status_code != 200:
            raise GroqApiError(resp.status_code, resp.text[:200])
        result = resp.json()
        content = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return content.strip()

    def _call_github_models(self, model: str, prompt: str, **kwargs: Any) -> str:
        if not self._gh_client:
            raise GithubModelsApiError(0, "No GH_TOKEN configured")
        # Strip HuggingFace-specific parameters, convert to OpenAI-compatible
        params = kwargs.pop("parameters", {})
        if isinstance(params, dict):
            if "max_new_tokens" in params:
                kwargs["max_tokens"] = params["max_new_tokens"]
            if "temperature" in params:
                kwargs["temperature"] = params["temperature"]
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        resp = self._gh_client.post(GITHUB_MODELS_URL, json=payload)
        if resp.status_code != 200:
            raise GithubModelsApiError(resp.status_code, resp.text[:200])
        result = resp.json()
        content = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return content.strip()

    def _call_gemini(self, prompt: str, **kwargs: Any) -> str:
        if not self._gemini_client:
            raise GeminiApiError(0, "No Gemini API key configured")
        generation_config: dict[str, Any] = {}
        params = kwargs.pop("parameters", {})
        if isinstance(params, dict):
            if "max_new_tokens" in params:
                generation_config["maxOutputTokens"] = params["max_new_tokens"]
            if "temperature" in params:
                generation_config["temperature"] = params["temperature"]
        if "max_tokens" in kwargs:
            generation_config["maxOutputTokens"] = kwargs.pop("max_tokens")
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs.pop("temperature")
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        if generation_config:
            payload["generationConfig"] = generation_config
        url = f"{GEMINI_URL}?key={self._gemini_key}"
        resp = self._gemini_client.post(url, json=payload)
        if resp.status_code != 200:
            raise GeminiApiError(resp.status_code, resp.text[:200])
        result = resp.json()
        candidates = result.get("candidates", [])
        if not candidates:
            raise GeminiApiError(0, "No candidates in Gemini response")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        return text.strip()

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
        # Tier 1: Gemini 2.5 Flash (1M token window, 1500 RPD, free)
        if self._gemini_client:
            try:
                return self._call_gemini(prompt, **kwargs)
            except GeminiApiError as e:
                print(f"  [gemini] failed: {e}")

        # Tier 2: GitHub Models GPT-4o-mini (8K input limit, 150 RPD, free)
        if self._gh_client:
            for model in GITHUB_MODELS_MODELS:
                try:
                    return self._call_github_models(model, prompt, **kwargs)
                except GithubModelsApiError as e:
                    print(f"  [gh-models] {model} failed: {e}")
                    continue

        # Tier 3: Groq (131K context, ~1000 RPD, fast)
        if self._groq_client:
            for model in GROQ_FREE_MODELS:
                try:
                    return self._call_groq(model, prompt, **kwargs)
                except GroqApiError as e:
                    print(f"  [groq] {model} failed: {e}")
                    continue

        # Tier 4: HF router (emergency fallback)
        models = self._discover_free_models()
        for m in FREE_MODELS:
            if m not in models:
                models.append(m)
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
