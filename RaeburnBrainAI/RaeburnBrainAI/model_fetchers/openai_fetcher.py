"""OpenAI-compatible fetcher (OpenAI, LiteLLM, custom gateways)."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher


class OpenAIFetcher(BaseFetcher):
    def _endpoint(self) -> str:
        base = self.meta.extras.get("endpoint") or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        if base.endswith("/chat/completions"):
            return base
        return base.rstrip("/") + "/chat/completions"

    def _api_key(self) -> Optional[str]:
        return self.meta.extras.get("api_key") or os.getenv("OPENAI_API_KEY")

    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        model_name = self.meta.extras.get("model") or self.meta.name
        endpoint = self._endpoint()
        api_key = self._api_key()
        allow_unauth = bool(self.meta.extras.get("allow_unauthenticated", False))

        start = time.monotonic()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif not allow_unauth:
            latency_ms = int((time.monotonic() - start) * 1000)
            return self._response(prompt + " - openai", latency_ms, "missing_api_key")

        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        content = ""
        error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(endpoint, headers=headers, json=payload)
                        resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content", "")
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, RetryError):
                error = str(exc.last_attempt.exception())
            else:
                error = str(exc)
        latency_ms = int((time.monotonic() - start) * 1000)
        if not content and not error:
            content = prompt + " - openai"
        return self._response(content, latency_ms, error)
