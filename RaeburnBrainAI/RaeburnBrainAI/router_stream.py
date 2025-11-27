"""Simple streaming facade that delegates to Router."""

from __future__ import annotations

from typing import AsyncIterator

from RaeburnBrainAI.router import Router


async def stream(prompt: str, session_id: str = "default") -> AsyncIterator[str]:
    router = Router()
    result = await router.route_first(prompt, session_id=session_id)
    yield result.content


__all__ = ["stream"]
