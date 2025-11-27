from __future__ import annotations

"""Judging and voting system for multi-model competitions."""

import json
from dataclasses import dataclass
from typing import Dict, Mapping

from .agent import AgentRegistry
from .model import BaseModelFetcher


@dataclass
class CompetitionResult:
    """Result of a model competition."""

    winner_id: str
    responses: Dict[str, str]


class Judge:
    """Run multi-model competitions using an external judge model."""

    def __init__(self, judge_model: BaseModelFetcher, registry: AgentRegistry) -> None:
        self.judge_model = judge_model
        self.registry = registry

    def compete(self, prompt: str, agents: Mapping[str, BaseModelFetcher]) -> CompetitionResult:
        """Return the winning agent ID after judging their responses."""
        # ensure agents exist
        for aid in agents:
            self.registry.ensure(aid, [])
        responses = {aid: fetcher.generate(prompt) for aid, fetcher in agents.items()}
        judge_prompt = json.dumps({"prompt": prompt, "responses": responses})
        winner = self.judge_model.generate(judge_prompt).strip()
        if winner not in agents:
            winner = next(iter(agents))
        for aid in agents:
            self.registry.record(aid, aid == winner)
        return CompetitionResult(winner_id=winner, responses=responses)


__all__ = ["CompetitionResult", "Judge"]

