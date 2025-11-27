"""Worker entrypoint for executing missions."""

from __future__ import annotations

from typing import Any, Dict

from BusinessFactory.mission_queue import MissionQueue, RouterAdapter
from BusinessFactory.mission_engine import execute_action


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Route LLM actions via queue/router; other actions via mission_engine
    action_type = payload.get("action_type", "llm")
    if action_type == "llm":
        queue = MissionQueue(router_adapter=RouterAdapter())
        return queue.submit(payload)
    return execute_action(payload, router=RouterAdapter())
