"""HuggingFace inference API fetcher."""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher


class HuggingFaceFetcher(BaseFetcher):
    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        model = self.meta.extras.get("model") or self.meta.name
        token = os.getenv("HF_API_TOKEN")
        start = time.monotonic()
        headers = {"Authorization": f"Bearer {token}" if token else ""}
        if not token:
            latency_ms = int((time.monotonic() - start) * 1000)
            return self._response(prompt + " - huggingface", latency_ms, "missing_api_token")

        content = ""
        error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(
                            f"https://api-inference.huggingface.co/models/{model}",
                            headers=headers,
                            json={"inputs": prompt},
                        )
                        resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                content = data[0].get("generated_text", "")
            else:
                content = data.get("generated_text", "")
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, RetryError):
                error = str(exc.last_attempt.exception())
            else:
                error = str(exc)
        latency_ms = int((time.monotonic() - start) * 1000)
        return self._response(content, latency_ms, error)
