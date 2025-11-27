"""Worker entrypoint for executing missions."""

from __future__ import annotations

from typing import Any, Dict

from BusinessFactory.mission_queue import MissionQueue


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    queue = MissionQueue()
    return queue.submit(payload)
