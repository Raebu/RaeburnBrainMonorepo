"""Mission progression logic with router integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from BusinessFactory.mission_queue import RouterCall, RouterAdapter, RouterPayload


@dataclass
class Mission:
    id: str
    description: str
    action_type: str = "llm"
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


def run_mission(mission: Mission, router_call: RouterCall | None = None) -> Dict[str, Any]:
    adapter = router_call or RouterAdapter().router_call_sync
    if mission.action_type == "llm":
        payload: RouterPayload = {
            "prompt": mission.description,
            **mission.payload,
        }
        result = adapter(payload)
        return {"mission_id": mission.id, "result": result}
    return {"mission_id": mission.id, "result": {"status": "skipped", "reason": "unsupported action"}}
