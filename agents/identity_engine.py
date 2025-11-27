"""Lookup and manage Raeburn agent personas."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


# Built-in agent definitions used if no external config is provided
DEFAULT_AGENTS: dict[str, dict] = {
    "generalist": {
        "name": "generalist",
        "system_prompt": "You are a versatile assistant able to tackle any task.",
    },
    "copywriter": {
        "name": "copywriter",
        "system_prompt": "You craft concise and compelling marketing copy.",
        "prompt_style": "energetic",
    },
}


class AgentModel(BaseModel):
    """Schema for validating agent definitions."""

    name: str
    system_prompt: str | None = None
    prompt_style: str | None = None
    capabilities: list[str] | None = None
    model_preferences: list[str] | None = None

    model_config = ConfigDict(extra="ignore")


def _load_agents_from_config(target: dict[str, dict]) -> None:
    path = os.getenv("RAEBURN_AGENT_CONFIG")
    if not path or not os.path.exists(path):
        return
    try:
        with open(path) as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return
        for role, cfg in raw.items():
            try:
                model = AgentModel(**cfg)
            except ValidationError:
                continue
            data = model.model_dump(exclude_none=True)
            if "name" not in data:
                data["name"] = role
            target[role] = data
    except Exception:  # noqa: BLE001
        return


@lru_cache(maxsize=1)
def _load_agents() -> dict[str, dict]:
    """Load agent definitions with optional overrides from config."""
    agents: dict[str, dict] = DEFAULT_AGENTS.copy()
    _load_agents_from_config(agents)
    return agents


def reload_agents() -> None:
    """Clear the cache and reload agents from config."""
    _load_agents.cache_clear()  # type: ignore[attr-defined]


def register_agent(role: str, **fields: Any) -> dict:
    """Dynamically register a new agent."""
    reload_agents()
    agents = _load_agents()
    fields.setdefault("name", role)
    model = AgentModel(**fields)
    agents[role] = model.model_dump(exclude_none=True)
    return agents[role]


def get_agent_by_role(role: str) -> dict:
    agents = _load_agents()
    return agents.get(role, agents["generalist"])


def list_agents() -> list[str]:
    """Return available agent roles."""
    return list(_load_agents().keys())

