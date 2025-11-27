"""Create new businesses and seed initial missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from BusinessFactory.mission_progression import Mission
from BusinessFactory.mission_queue import RouterCall, RouterAdapter


@dataclass
class Business:
    business_id: str
    teams: List[str]
    missions: List[Mission] = field(default_factory=list)


class BusinessFactory:
    def __init__(self, router_call: RouterCall | None = None) -> None:
        self.router_call = router_call or RouterAdapter()
        self._businesses: Dict[str, Business] = {}

    def create_business(self, business_id: str, teams: List[str]) -> Business:
        biz = Business(business_id=business_id, teams=teams)
        initial_mission = Mission(
            id=f"mission-{business_id}-0",
            description=f"Draft launch plan for {business_id}",
            action_type="llm",
            payload={"session_id": f"biz-{business_id}"},
            tags=["strategy"],
        )
        biz.missions.append(initial_mission)
        self._businesses[business_id] = biz
        return biz

    def run_initial_plan(self, business_id: str) -> Dict[str, Any]:
        biz = self._businesses[business_id]
        if not biz.missions:
            return {"status": "no_missions"}
        mission = biz.missions[0]
        result = self.router_call({"prompt": mission.description, **mission.payload})
        return {"business_id": business_id, "mission_id": mission.id, "result": result}


__all__ = ["BusinessFactory", "Business", "Mission"]
