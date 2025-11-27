"""Queue adapter for mission execution with sync+async router calls."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional, Protocol, TypedDict

from tenacity import retry, stop_after_attempt, wait_exponential

from RaeburnBrainAI.router import Router, RouterRequest, RouterResponse


class RouterPayload(TypedDict, total=False):
    action_type: str
    prompt: str
    model_hint: Optional[str]
    context: Optional[str]
    session_id: Optional[str]
    stream: bool


class RouterCall(Protocol):
    def __call__(self, payload: RouterPayload) -> Dict[str, Any]:
        ...


def _make_request(payload: RouterPayload) -> RouterRequest:
    return RouterRequest(
        prompt=payload.get("prompt", "") or "",
        session_id=payload.get("session_id", "queue") or "queue",
        task=payload.get("action_type"),
        require_streaming=bool(payload.get("stream", False)),
    )


class RouterAdapter:
    """Expose sync and async router calls with retry/backoff."""

    def __init__(self, router: Router | None = None) -> None:
        self.router = router or Router()

    async def router_call_async(self, payload: RouterPayload) -> Dict[str, Any]:
        req = _make_request(payload)
        response = await self._route_with_retry(req)
        return self._to_result(response, stream=bool(payload.get("stream", False)))

    def router_call_sync(self, payload: RouterPayload) -> Dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.run_until_complete(self.router_call_async(payload))  # type: ignore[arg-type]
        return asyncio.run(self.router_call_async(payload))  # type: ignore[arg-type]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    async def _route_with_retry(self, request: RouterRequest) -> RouterResponse:
        return await self.router.route_first(
            prompt=request.prompt,
            session_id=request.session_id,
            task=request.task,
            require_json=request.require_json,
            require_streaming=request.require_streaming,
            required_roles=request.required_roles,
        )

    @staticmethod
    def _to_result(response: RouterResponse, *, stream: bool) -> Dict[str, Any]:
        result = {
            "model": response.model,
            "content": response.content,
            "latency": response.latency,
            "error": response.error,
            "score": response.score,
        }
        if stream:
            result["stream"] = [response.content]
        return result


class MissionQueue:
    def __init__(self, router_adapter: RouterAdapter | None = None) -> None:
        self.router_adapter = router_adapter or RouterAdapter()
        self.enabled = os.getenv("RAEBURN_AUTONOMY_QUEUE_ENABLED", "false").lower() == "true"

    def submit(self, payload: RouterPayload) -> Dict[str, Any]:
        if not self.enabled:
            return self.router_adapter.router_call_sync(payload)
        # Queue mode placeholder: in the future push to workers.
        return self.router_adapter.router_call_sync(payload)
