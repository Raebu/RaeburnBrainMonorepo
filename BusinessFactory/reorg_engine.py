"""Reorg engine for agent reassignment across businesses."""

from __future__ import annotations

from typing import Dict, List


def reassign_agent(business_agents: Dict[str, List[str]], agent: str, target_business: str) -> Dict[str, List[str]]:
    """Move an agent to a new business, returning updated mapping."""
    updated = {k: list(v) for k, v in business_agents.items()}
    for agents in updated.values():
        if agent in agents:
            agents.remove(agent)
    updated.setdefault(target_business, []).append(agent)
    return updated
