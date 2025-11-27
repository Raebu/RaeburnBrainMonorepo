"""Mission engine dispatching to router, scraper, verifier, or scheduler."""

from __future__ import annotations

from typing import Any, Dict

from BusinessFactory.mission_queue import RouterAdapter, RouterPayload
from RaeburnBrainAI.memory import MemoryStore

from Scraper.web_scraper import scrape  # type: ignore[attr-defined]
from Verifier.fact_checker import verify  # type: ignore[attr-defined]


def _audit(agent_id: str, text: str, *, tags: list[str] | None = None) -> None:
    """Write an audit log into the memory store (best effort)."""
    try:
        MemoryStore().write(agent_id=agent_id, text=text, tags=tags or ["audit"], importance=0.4)
    except Exception:
        pass


def execute_action(payload: Dict[str, Any], router: RouterAdapter | None = None) -> Dict[str, Any]:
    """Route actions to the correct subsystem."""
    action_type = payload.get("action_type", "llm")
    agent_id = payload.get("agent_id", "global")
    tags = payload.get("tags", [])
    router = router or RouterAdapter()

    if action_type == "llm":
        req: RouterPayload = {
            "prompt": payload.get("prompt", ""),
            "session_id": payload.get("session_id", "mission"),
            "action_type": action_type,
            "stream": bool(payload.get("stream", False)),
        }
        result = router.router_call_sync(req)
        _audit(agent_id, f"LLM action result: {result}", tags=[*tags, "llm"])
        return result

    if action_type == "scrape":
        target = payload.get("url") or ""
        result = {"status": "ok", "url": target, "content": scrape(target) if callable(scrape) else ""}  # type: ignore[arg-type]
        _audit(agent_id, f"Scrape action for {target}", tags=[*tags, "scrape"])
        return result

    if action_type == "verify":
        data = payload.get("data") or {}
        result = verify(data) if callable(verify) else {"status": "unknown"}  # type: ignore[arg-type]
        _audit(agent_id, f"Verify action: {result}", tags=[*tags, "verify"])
        return result

    # fallback: just log the request
    _audit(agent_id, f"Unsupported action_type={action_type}", tags=[*tags, "unsupported"])
    return {"status": "skipped", "reason": f"unsupported action_type {action_type}"}
