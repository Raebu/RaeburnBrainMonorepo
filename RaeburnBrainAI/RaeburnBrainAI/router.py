"""Router entrypoint for RaeburnBrainAI.

Routes prompts across configured models, applying capability gating, health
filters, and bias-aware scoring.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from RaeburnBrainAI.model import ModelRegistry, ModelMeta
from RaeburnBrainAI.scoring import hybrid_score


@dataclass
class RouterRequest:
    prompt: str
    session_id: str = "default"
    parallel: bool = True
    limit_models: Optional[int] = None
    task: Optional[str] = None
    require_json: bool = False
    require_streaming: bool = False
    required_roles: Sequence[str] | None = None


@dataclass
class RouterResponse:
    model: str
    content: str
    latency: int
    error: Optional[str]
    raw: Dict[str, Any]
    score: float


class Router:
    def __init__(self, registry: Optional[ModelRegistry] = None) -> None:
        self.registry = registry or ModelRegistry.load_default()

    def _bias_multiplier(self, meta: ModelMeta, fetcher: Any, task: Optional[str]) -> float:
        bias = 1.0
        if task:
            if task in meta.router_bias.prefer_for:
                bias *= 1.2
            if task in meta.router_bias.avoid_for:
                bias *= 0.7
            if task in meta.strengths:
                bias *= 1.15
            if task in meta.weaknesses:
                bias *= 0.85
        # cost and speed influence
        bias *= 1.0 / (1.0 + max(meta.cost_usd_per_1k, 0.0))
        if meta.speed_tps_estimate:
            bias *= 1.0 + min(meta.speed_tps_estimate, 100.0) / 1000.0
        if getattr(fetcher, "failure_count", 0):
            bias *= max(0.2, 1.0 - 0.1 * getattr(fetcher, "failure_count", 0))
        if not getattr(fetcher, "health_ok", True):
            bias *= 0.8
        if meta.last_passed_health is None:
            bias *= 0.9
        return bias

    async def route(self, request: RouterRequest | str) -> List[RouterResponse]:
        if isinstance(request, str):
            request = RouterRequest(prompt=request)
        fetchers = self.registry.choose(
            request.limit_models,
            task=request.task,
            require_json=request.require_json,
            require_streaming=request.require_streaming,
            required_roles=request.required_roles,
        )
        tasks = [f.generate(request.prompt, request.session_id) for f in fetchers]
        responses: List[Dict[str, Any]] = []
        if request.parallel:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, fetcher in zip(results, fetchers):
                if isinstance(res, Exception):
                    responses.append(
                        {
                            "model": fetcher.name,
                            "content": "",
                            "latency": 0,
                            "error": str(res),
                            "meta": fetcher.meta,
                            "health_ok": getattr(fetcher, "health_ok", True),
                            "failure_count": getattr(fetcher, "failure_count", 0),
                        }
                    )
                else:
                    responses.append(res)
        else:
            for fetcher in fetchers:
                try:
                    responses.append(await fetcher.generate(request.prompt, request.session_id))
                except Exception as exc:  # noqa: BLE001
                    responses.append(
                        {
                            "model": fetcher.name,
                            "content": "",
                            "latency": 0,
                            "error": str(exc),
                            "meta": fetcher.meta,
                            "health_ok": getattr(fetcher, "health_ok", True),
                            "failure_count": getattr(fetcher, "failure_count", 0),
                        }
                    )

        routed: List[RouterResponse] = []
        for res in responses:
            meta: ModelMeta = res.get("meta") or ModelMeta(name=res.get("model", ""), provider="local")
            fetcher = next((f for f in fetchers if f.name == meta.name), None)
            bias = self._bias_multiplier(meta, fetcher or object(), request.task)
            routed.append(
                RouterResponse(
                    model=str(res.get("model")),
                    content=str(res.get("content", "")),
                    latency=int(res.get("latency", 0)),
                    error=res.get("error"),
                    raw=res,
                    score=hybrid_score(request.prompt, res) * bias,
                )
            )
        routed.sort(key=lambda r: r.score, reverse=True)
        return routed

    async def route_first(self, prompt: str, session_id: str = "default", **kwargs: Any) -> RouterResponse:
        responses = await self.route(RouterRequest(prompt=prompt, session_id=session_id, **kwargs))
        return responses[0]


__all__ = ["Router", "RouterRequest", "RouterResponse"]
