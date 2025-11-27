"""Utility functions for scoring text responses."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Awaitable, Callable
import os
import json
import importlib

# Imported at module scope so tests can monkeypatch ``route_prompt`` easily
try:
    from core.router import route_prompt
except Exception:  # pragma: no cover - router not available
    route_prompt = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer, util  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = Any  # type: ignore[misc, assignment]
    util = None  # type: ignore[assignment]

_EMBED_MODEL: SentenceTransformer | None = None
_PLUGIN: Callable[..., Awaitable[float]] | Callable[..., float] | None = None


def _get_plugin() -> Callable[..., Awaitable[float]] | Callable[..., float] | None:
    """Load a custom scoring plugin from ``RAEBURN_SCORING_PLUGIN``."""
    global _PLUGIN
    if _PLUGIN is not None:
        return _PLUGIN
    path = os.getenv("RAEBURN_SCORING_PLUGIN")
    if not path:
        return None
    try:
        module, func_name = path.rsplit(".", 1)
        mod = importlib.import_module(module)
        _PLUGIN = getattr(mod, func_name)
    except Exception:  # pragma: no cover - plugin import failure
        _PLUGIN = None
    return _PLUGIN


async def _model_similarity(a: str, b: str) -> float:
    """Return a similarity score from an external model."""
    # If the router cannot be imported, fall back to simple similarity
    if route_prompt is None:  # type: ignore[truthy-bool]
        return SequenceMatcher(None, a, b).ratio()

    prompt = (
        "You are a helpful judge. Score how well the following response answers "
        "the prompt on a scale from 0 to 1.\n"
        f"PROMPT: {a}\nRESPONSE: {b}\nScore:"
    )
    try:
        results = await route_prompt(prompt, agent={"name": "judge"}, session_id="scoring")
        if results:
            content = results[0].get("content", "0")
            return max(0.0, min(1.0, float(content.strip())))
    except Exception:  # pragma: no cover - network failure
        return SequenceMatcher(None, a, b).ratio()
    return SequenceMatcher(None, a, b).ratio()


def _embedding_similarity(a: str, b: str) -> float:
    """Return cosine similarity using sentence embeddings."""
    global _EMBED_MODEL
    if SentenceTransformer is None or util is None:
        return SequenceMatcher(None, a, b).ratio()
    if _EMBED_MODEL is None:
        model_name = os.getenv("RAEBURN_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _EMBED_MODEL = SentenceTransformer(model_name)
    emb1 = _EMBED_MODEL.encode(a, convert_to_tensor=True)
    emb2 = _EMBED_MODEL.encode(b, convert_to_tensor=True)
    return float(util.cos_sim(emb1, emb2).item())


async def semantic_similarity(a: str, b: str) -> float:
    """Return a similarity ratio between two strings in the range 0-1."""
    if not a or not b:
        return 0.0
    backend = os.getenv("RAEBURN_SCORING_BACKEND")
    if backend == "embedding":
        try:
            return _embedding_similarity(a, b)
        except Exception:  # pragma: no cover - fallback
            return SequenceMatcher(None, a, b).ratio()
    if backend == "model":
        try:
            return await _model_similarity(a, b)
        except Exception:  # pragma: no cover - fallback
            return SequenceMatcher(None, a, b).ratio()
    return SequenceMatcher(None, a, b).ratio()


def _weights() -> tuple[float, float, float, float]:
    """Return scoring weights from ``RAEBURN_SCORE_WEIGHTS``."""
    env = os.getenv("RAEBURN_SCORE_WEIGHTS")
    if env:
        try:
            if env.strip().startswith("{"):
                data = json.loads(env)
                length = float(data.get("length", 0.15))
                match = float(data.get("match", 0.25))
                sim = float(data.get("similarity", 0.45))
                latency = float(data.get("latency", 0.15))
            else:
                parts = [float(x) for x in env.split(",")]
                length, match, sim, latency = parts[:4]
            total = length + match + sim + latency
            if total:
                return (
                    length / total,
                    match / total,
                    sim / total,
                    latency / total,
                )
        except Exception:
            pass
    return 0.15, 0.25, 0.45, 0.15
