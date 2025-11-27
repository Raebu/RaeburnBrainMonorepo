"""Scoring based judging utilities."""

from __future__ import annotations

import re
import inspect
import os
from typing import Iterable, Tuple, Dict

from core.router import route_prompt
from .scoring import semantic_similarity, _weights, _get_plugin


async def _score_candidate(
    content: str,
    error: str | None,
    user_input: str,
    user_tokens: set[str],
    latency: int,
    feedback: float | None = None,
) -> float:
    """Return a 0-1 score for a candidate response."""
    if error:
        return 0.0

    length_score = min(len(content) / 100, 1.0)
    match_score = (
        sum(1 for t in user_tokens if t in content.lower()) / len(user_tokens)
        if user_tokens
        else 0.0
    )
    sim_score = await semantic_similarity(user_input.lower(), content.lower())
    latency_score = max(0.0, 1 - latency / 5000)
    length_w, match_w, sim_w, latency_w = _weights()
    score = (
        length_w * length_score
        + match_w * match_score
        + sim_w * sim_score
        + latency_w * latency_score
    )

    plugin = _get_plugin()
    if plugin is not None:
        try:
            result = plugin(
                content=content,
                user_input=user_input,
                latency=latency,
                feedback=feedback,
                error=error,
            )
            if inspect.isawaitable(result):
                result = await result
            score = float(result)
        except Exception:  # pragma: no cover - plugin failure
            pass

    if feedback is not None:
        weight = float(os.getenv("RAEBURN_FEEDBACK_WEIGHT", "0.2"))
        score = (1 - weight) * score + weight * float(feedback)

    return round(score, 3)


async def _rule_judge(candidates: Iterable[dict], user_input: str) -> Tuple[dict, Dict[str, float]]:
    """Rank candidate model outputs using rule-based heuristics."""

    tokens = set(re.findall(r"\w+", user_input.lower()))
    scores: Dict[str, float] = {}
    best: dict | None = None
    best_score = -1.0

    for cand in candidates:
        content = cand.get("content", "")
        error = cand.get("error")
        latency = int(cand.get("latency", 0))
        feedback = cand.get("feedback")
        score = await _score_candidate(content, error, user_input, tokens, latency, feedback)
        scores[cand["id"]] = score
        if score > best_score:
            best = cand
            best_score = score

    assert best is not None
    return best, scores


async def _model_judge(candidates: list[dict], user_input: str) -> Tuple[dict, Dict[str, float]]:
    """Use a language model to pick the best answer."""
    prompt_lines = [
        "You are a judge choosing the best answer to the user's question.",
        f"QUESTION: {user_input}",
        "ANSWERS:",
    ]
    for idx, cand in enumerate(candidates, 1):
        prompt_lines.append(f"{idx}. {cand.get('content','')}")
    prompt_lines.append("Respond with the number of the best answer.")
    prompt = "\n".join(prompt_lines)
    try:
        if route_prompt is None:  # pragma: no cover
            raise RuntimeError("router unavailable")
        results = await route_prompt(prompt, agent={"name": "judge"}, session_id="judge")
        if results:
            import re
            m = re.search(r"\d+", results[0].get("content", ""))
            if m:
                idx = int(m.group()) - 1
                if 0 <= idx < len(candidates):
                    best_idx = idx
                else:
                    best_idx = 0
            else:
                best_idx = 0
        else:
            best_idx = 0
    except Exception:  # pragma: no cover - network failure
        best_idx = 0

    best_rule, scores = await _rule_judge(candidates, user_input)
    return candidates[best_idx], scores


async def judge_outputs(
    candidates: Iterable[dict], user_input: str
) -> Tuple[dict, Dict[str, float]]:
    """Rank candidate model outputs using the configured backend."""

    backend = os.getenv("RAEBURN_JUDGE_BACKEND")
    cand_list = list(candidates)
    if backend == "model":
        try:
            return await _model_judge(cand_list, user_input)
        except Exception:
            pass
    return await _rule_judge(cand_list, user_input)
