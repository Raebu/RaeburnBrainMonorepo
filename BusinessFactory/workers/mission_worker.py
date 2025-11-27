"""Worker entrypoint for executing missions."""

from __future__ import annotations

from typing import Any, Dict

from BusinessFactory.mission_queue import MissionQueue, RouterAdapter, RouterPayload


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    queue = MissionQueue(router_adapter=RouterAdapter())
    return queue.submit(payload)  # payload should conform to RouterPayload
