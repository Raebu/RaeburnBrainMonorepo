"""Heartbeat loop placeholder for mission execution."""

from __future__ import annotations

from typing import Dict, Any

from BusinessFactory.mission_progression import Mission, run_mission
from BusinessFactory.mission_queue import RouterCall, RouterAdapter


def heartbeat(mission: Mission, router_call: RouterCall | None = None) -> Dict[str, Any]:
    caller = router_call or RouterAdapter()
    return run_mission(mission, router_call=caller)
