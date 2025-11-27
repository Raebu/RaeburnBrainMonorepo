"""Queue adapter for mission execution."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Protocol

from RaeburnBrainAI.router import Router, RouterRequest, RouterResponse


class RouterCall(Protocol):
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...


class RouterAdapter:
    def __init__(self, router: Router | None = None) -> None:
        self.router = router or Router()

    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt", "")
        session_id = payload.get("session_id", "queue")
        response: RouterResponse = asyncio.run(
            self.router.route_first(prompt, session_id=session_id)
        )
        return {
            "model": response.model,
            "content": response.content,
            "latency": response.latency,
            "error": response.error,
            "score": response.score,
        }


class MissionQueue:
    def __init__(self, router_call: RouterCall | None = None) -> None:
        self.router_call = router_call or RouterAdapter()
        self.enabled = os.getenv("RAEBURN_AUTONOMY_QUEUE_ENABLED", "false").lower() == "true"

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return self.router_call(payload)
        # Queue mode placeholder: in the future push to workers.
        return self.router_call(payload)
