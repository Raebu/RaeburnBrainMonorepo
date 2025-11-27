"""OpenRouter fetcher implementation."""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher


class OpenRouterFetcher(BaseFetcher):
    def _endpoint(self) -> str:
        return self.meta.extras.get("endpoint") or "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        model = self.meta.extras.get("model") or self.meta.name
        api_key = os.getenv("OPENROUTER_API_KEY")
        start = time.monotonic()
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "HTTP-Referer": "https://raeburn.ai",
            "X-Title": "RaeburnBrainAI",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if not api_key:
            latency_ms = int((time.monotonic() - start) * 1000)
            return self._response(prompt + " - openrouter", latency_ms, "missing_api_key")

        content = ""
        error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(self._endpoint(), json=payload, headers=headers)
                        resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"].get("content", "")
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, RetryError):
                error = str(exc.last_attempt.exception())
            else:
                error = str(exc)
        latency_ms = int((time.monotonic() - start) * 1000)
        return self._response(content, latency_ms, error)
