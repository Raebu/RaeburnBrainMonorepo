"""Local echo fetcher used as default fallback."""

from __future__ import annotations

import time
from typing import Any, Dict

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher


class LocalFetcher(BaseFetcher):
    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        start = time.monotonic()
        latency_ms = int((time.monotonic() - start) * 1000)
        return self._response(f"{prompt} [local:{self.name}]", latency_ms, None)
