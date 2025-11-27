"""Hybrid scoring for router responses."""

from __future__ import annotations

import os
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict


@dataclass
class ScoreWeights:
    length: float = 0.15
    match: float = 0.25
    similarity: float = 0.45
    latency: float = 0.15

    @classmethod
    def from_env(cls) -> "ScoreWeights":
        env = os.getenv("RAEBURN_SCORE_WEIGHTS")
        if not env:
            return cls()
        try:
            if env.strip().startswith("{"):
                import json

                data = json.loads(env)
                return cls(
                    length=float(data.get("length", cls.length)),
                    match=float(data.get("match", cls.match)),
                    similarity=float(data.get("similarity", cls.similarity)),
                    latency=float(data.get("latency", cls.latency)),
                )
            parts = [float(x) for x in env.split(",")]
            return cls(*parts[:4])
        except Exception:
            return cls()

    def normalized(self) -> "ScoreWeights":
        total = self.length + self.match + self.similarity + self.latency
        if total == 0:
            return ScoreWeights()
        return ScoreWeights(
            length=self.length / total,
            match=self.match / total,
            similarity=self.similarity / total,
            latency=self.latency / total,
        )


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def hybrid_score(prompt: str, response: Dict[str, Any], weights: ScoreWeights | None = None) -> float:
    weights = (weights or ScoreWeights.from_env()).normalized()
    content = response.get("content", "") or ""
    latency = float(response.get("latency") or 0.0)
    error = response.get("error")
    length_score = min(len(content), 4000) / 4000.0
    match_score = 0.0 if error else 1.0
    sim_score = _similarity(prompt, content)
    latency_score = 1.0 / (1.0 + max(latency, 1.0))
    return (
        length_score * weights.length
        + match_score * weights.match
        + sim_score * weights.similarity
        + latency_score * weights.latency
    )
