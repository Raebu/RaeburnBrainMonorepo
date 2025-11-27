"""Mission progression logic with router integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from BusinessFactory.mission_queue import RouterCall, RouterAdapter


@dataclass
class Mission:
    id: str
    description: str
    action_type: str = "llm"
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


def run_mission(mission: Mission, router_call: RouterCall | None = None) -> Dict[str, Any]:
    caller = router_call or RouterAdapter()
    if mission.action_type == "llm":
        payload = {"prompt": mission.description, **mission.payload}
        result = caller(payload)
        return {"mission_id": mission.id, "result": result}
    return {"mission_id": mission.id, "result": {"status": "skipped", "reason": "unsupported action"}}
