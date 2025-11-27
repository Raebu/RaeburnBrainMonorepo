"""Model registry backed by config files with rich metadata and capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from RaeburnBrainAI.config import load_installed_models, load_model_registry
from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher
from RaeburnBrainAI.model_fetchers.huggingface_fetcher import HuggingFaceFetcher
from RaeburnBrainAI.model_fetchers.local_fetcher import LocalFetcher
from RaeburnBrainAI.model_fetchers.ollama_fetcher import OllamaFetcher
from RaeburnBrainAI.model_fetchers.openai_fetcher import OpenAIFetcher
from RaeburnBrainAI.model_fetchers.openrouter_fetcher import OpenRouterFetcher


@dataclass
class RouterBias:
    prefer_for: List[str] = field(default_factory=list)
    avoid_for: List[str] = field(default_factory=list)


@dataclass
class Capabilities:
    streaming: bool = False
    json_mode: bool = False
    roles_supported: List[str] = field(default_factory=lambda: ["user"])
    multimodal: bool = False
    max_context: Optional[int] = None


@dataclass
class ModelMeta:
    name: str
    provider: str
    cost_usd_per_1k: float = 0.0
    speed_tps_estimate: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    forbidden_tasks: List[str] = field(default_factory=list)
    router_bias: RouterBias = field(default_factory=RouterBias)
    auto_disable_threshold_failures: Optional[int] = None
    last_passed_health: Optional[str] = None
    allowed_hosts: List[str] = field(default_factory=list)
    capabilities: Capabilities = field(default_factory=Capabilities)
    extras: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMeta":
        provider = str(data.get("provider") or data.get("type") or "local").lower()
        cost = data.get("cost") or {}
        if isinstance(cost, (int, float)):
            cost_usd = float(cost)
        else:
            cost_usd = float(cost.get("usd_per_1k", cost.get("usd_per_k", 0.0)) or 0.0)
        speed = data.get("speed") or {}
        speed_tps = float(speed.get("tps_estimate", speed.get("tps", 0.0)) or 0.0)
        router_bias = data.get("router_bias") or {}
        capabilities = data.get("capabilities") or {}
        strengths = list(data.get("strengths") or [])
        weaknesses = list(data.get("weaknesses") or [])
        forbidden_tasks = list(data.get("forbidden_tasks") or [])
        allowed_hosts = list(data.get("allowed_hosts") or [])
        auto_disable = data.get("auto_disable_threshold_failures")
        last_passed_health = data.get("last_passed_health")

        caps = Capabilities(
            streaming=bool(capabilities.get("streaming", False)),
            json_mode=bool(capabilities.get("json_mode", False)),
            roles_supported=list(capabilities.get("roles_supported", [])) or ["user"],
            multimodal=bool(capabilities.get("multimodal", capabilities.get("multi_modality", False))),
            max_context=capabilities.get("max_context"),
        )

        bias = RouterBias(
            prefer_for=list(router_bias.get("prefer_for", [])),
            avoid_for=list(router_bias.get("avoid_for", [])),
        )

        extras = {k: v for k, v in data.items() if k not in {
            "name",
            "id",
            "provider",
            "type",
            "cost",
            "speed",
            "strengths",
            "weaknesses",
            "forbidden_tasks",
            "router_bias",
            "auto_disable_threshold_failures",
            "last_passed_health",
            "allowed_hosts",
            "capabilities",
        }}

        # Provider defaults for capabilities and auth behavior
        if provider in {"openai", "openai_compatible", "litelm", "openrouter"}:
            caps.streaming = capabilities.get("streaming", True)
            caps.json_mode = capabilities.get("json_mode", True)
            caps.roles_supported = capabilities.get("roles_supported", ["system", "user", "assistant"])
        if provider == "litelm":
            extras.setdefault("allow_unauthenticated", True)
        if provider == "openrouter":
            extras.setdefault("endpoint", "https://openrouter.ai/api/v1/chat/completions")
        if provider == "huggingface":
            caps.streaming = capabilities.get("streaming", False)
            caps.json_mode = capabilities.get("json_mode", False)

        return cls(
            name=str(data.get("name") or data.get("id") or ""),
            provider=provider,
            cost_usd_per_1k=cost_usd,
            speed_tps_estimate=speed_tps,
            strengths=strengths,
            weaknesses=weaknesses,
            forbidden_tasks=forbidden_tasks,
            router_bias=bias,
            auto_disable_threshold_failures=int(auto_disable) if auto_disable is not None else None,
            last_passed_health=last_passed_health,
            allowed_hosts=allowed_hosts,
            capabilities=caps,
            extras=extras,
        )

    def host_allowed(self, endpoint: str | None) -> bool:
        if not self.allowed_hosts:
            return True
        if not endpoint:
            return True
        host = urlparse(endpoint).hostname
        if not host:
            return True
        return host in self.allowed_hosts


class ModelRegistry:
    """Loads models from config and instantiates fetchers."""

    def __init__(self, registry: Dict[str, Any] | None = None, installed: Dict[str, Any] | None = None):
        self._registry = registry or load_model_registry()
        self._installed = installed or load_installed_models()
        self._metas = self._parse_models(self._registry, self._installed)
        self._fetcher_cache: Dict[str, BaseFetcher] = {}

    @staticmethod
    def _parse_models(registry: Dict[str, Any], installed: Dict[str, Any]) -> List[ModelMeta]:
        models = registry.get("models") or []
        metas: List[ModelMeta] = []
        for model in models:
            meta = ModelMeta.from_dict(model)
            if not meta.name:
                continue
            install_info = installed.get(meta.name, {}) if isinstance(installed, dict) else {}
            meta.extras.setdefault("installed", install_info.get("installed", True))
            if install_info.get("endpoint"):
                meta.extras.setdefault("endpoint", install_info.get("endpoint"))
            metas.append(meta)
        if not metas:
            metas.append(ModelMeta(name="local-echo", provider="local"))
        return metas

    def models(self) -> List[ModelMeta]:
        return list(self._metas)

    def get(self, name: str) -> Optional[ModelMeta]:
        for meta in self._metas:
            if meta.name == name:
                return meta
        return None

    def _build_fetcher(self, meta: ModelMeta) -> BaseFetcher:
        provider = meta.provider.lower()
        if provider == "openrouter":
            return OpenRouterFetcher(meta.name, meta)
        if provider in {"openai", "openai_compatible", "litelm"}:
            return OpenAIFetcher(meta.name, meta)
        if provider == "huggingface":
            return HuggingFaceFetcher(meta.name, meta)
        if provider == "ollama":
            return OllamaFetcher(meta.name, meta)
        return LocalFetcher(meta.name, meta)

    def fetcher_for(self, meta: ModelMeta) -> BaseFetcher:
        if meta.name in self._fetcher_cache:
            return self._fetcher_cache[meta.name]
        fetcher = self._build_fetcher(meta)
        self._fetcher_cache[meta.name] = fetcher
        return fetcher

    def choose(
        self,
        limit: Optional[int] = None,
        *,
        task: Optional[str] = None,
        require_json: bool = False,
        require_streaming: bool = False,
        required_roles: Sequence[str] | None = None,
    ) -> List[BaseFetcher]:
        selected: List[BaseFetcher] = []
        for meta in self._metas:
            if task and task in meta.forbidden_tasks:
                continue
            fetcher = self.fetcher_for(meta)
            if meta.auto_disable_threshold_failures is not None and fetcher.failure_count >= meta.auto_disable_threshold_failures:
                continue
            if require_json and not meta.capabilities.json_mode:
                continue
            if require_streaming and not meta.capabilities.streaming:
                continue
            if required_roles:
                if not all(role in meta.capabilities.roles_supported for role in required_roles):
                    continue
            endpoint = meta.extras.get("endpoint") if isinstance(meta.extras, dict) else None
            if not meta.host_allowed(endpoint):
                continue
            selected.append(fetcher)
            if limit and len(selected) >= limit:
                break
        if not selected:
            selected.append(self.fetcher_for(ModelMeta(name="local-echo", provider="local")))
        return selected

    @classmethod
    def load_default(cls) -> "ModelRegistry":
        return cls()


__all__ = ["ModelRegistry", "ModelMeta", "Capabilities", "RouterBias"]
