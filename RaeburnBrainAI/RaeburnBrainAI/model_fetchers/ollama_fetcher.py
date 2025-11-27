"""Ollama fetcher stub with graceful fallback."""

from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher


class OllamaFetcher(BaseFetcher):
    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        model = self.meta.extras.get("model") or self.meta.name
        url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        start = time.monotonic()
        content = ""
        error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json={"model": model, "prompt": prompt})
                resp.raise_for_status()
                data = resp.json()
                content = data.get("response") or data.get("output") or ""
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        latency_ms = int((time.monotonic() - start) * 1000)
        return self._response(content or prompt + " - ollama", latency_ms, error)
