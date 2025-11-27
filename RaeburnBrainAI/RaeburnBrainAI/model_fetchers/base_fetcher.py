"""Base fetcher interface for provider-specific implementations."""

from __future__ import annotations

import time
from typing import Any, Dict

from RaeburnBrainAI.model.registry import ModelMeta


class BaseFetcher:
    def __init__(self, name: str, meta: ModelMeta) -> None:
        self.name = name
        self.meta = meta
        self.health_ok: bool = True
        self.failure_count: int = 0
        self.recent_latency_avg: float = 0.0

    def _record(self, latency_ms: int, error: str | None) -> None:
        alpha = 0.2
        if self.recent_latency_avg == 0.0:
            self.recent_latency_avg = float(latency_ms)
        else:
            self.recent_latency_avg = alpha * float(latency_ms) + (1 - alpha) * self.recent_latency_avg
        if error:
            self.failure_count += 1
            self.health_ok = False
        else:
            self.health_ok = True

    def _response(self, content: str, latency_ms: int, error: str | None = None) -> Dict[str, Any]:
        self._record(latency_ms, error)
        return {
            "id": self.name,
            "model": self.name,
            "content": content,
            "latency": latency_ms,
            "error": error,
            "meta": self.meta,
            "health_ok": self.health_ok,
            "failure_count": self.failure_count,
            "recent_latency_avg": self.recent_latency_avg,
        }

    async def generate(self, prompt: str, session_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def probe(self) -> bool:
        """Optional health probe."""
        start = time.monotonic()
        try:
            await self.generate("ping", session_id="health")
            return True
        except Exception:
            return False
        finally:
            _ = time.monotonic() - start
