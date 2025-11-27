# Core engine components for Raeburn Brain AI
from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from random import betavariate, random
import time
from typing import Awaitable, Callable, Sequence
import logging
import threading

from .memory import (
    BaseMemoryBackend,
    InMemoryBackend,
    MemoryEntry,
    MEMORY_OP_COUNT,
    MEMORY_OP_LATENCY,
)
from prometheus_client import Counter, Histogram


class MemoryStore:
    """Store agent memories using a pluggable backend."""

    def __init__(self, backend: BaseMemoryBackend | None = None) -> None:
        self.backend = backend or InMemoryBackend()

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] | None = None,
        importance: float = 0.5,
    ) -> None:
        start = time.perf_counter()
        self.backend.add(agent_id, text, tags=tags or (), importance=importance)
        MEMORY_OP_COUNT.labels("add").inc()
        MEMORY_OP_LATENCY.labels("add").observe(time.perf_counter() - start)

    async def aadd(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] | None = None,
        importance: float = 0.5,
    ) -> None:
        self.add(agent_id, text, tags=tags, importance=importance)

    def get(self, agent_id: str, limit: int = 5) -> list[MemoryEntry]:
        start = time.perf_counter()
        result = self.backend.get(agent_id, limit=limit)
        MEMORY_OP_COUNT.labels("get").inc()
        MEMORY_OP_LATENCY.labels("get").observe(time.perf_counter() - start)
        return result

    async def aget(self, agent_id: str, limit: int = 5) -> list[MemoryEntry]:
        return self.get(agent_id, limit=limit)

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        start = time.perf_counter()
        result = self.backend.search(agent_id, query, limit=limit)
        MEMORY_OP_COUNT.labels("search").inc()
        MEMORY_OP_LATENCY.labels("search").observe(time.perf_counter() - start)
        return result

    def similar(self, agent_id: str, text: str, limit: int = 5) -> list[MemoryEntry]:
        start = time.perf_counter()
        result = self.backend.similar(agent_id, text, limit=limit)
        MEMORY_OP_COUNT.labels("similar").inc()
        MEMORY_OP_LATENCY.labels("similar").observe(time.perf_counter() - start)
        return result

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> list[MemoryEntry]:
        start = time.perf_counter()
        result = self.backend.by_tag(agent_id, tag, limit=limit)
        MEMORY_OP_COUNT.labels("tag").inc()
        MEMORY_OP_LATENCY.labels("tag").observe(time.perf_counter() - start)
        return result

    async def asearch(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        return self.search(agent_id, query, limit=limit)

    async def asimilar(self, agent_id: str, text: str, limit: int = 5) -> list[MemoryEntry]:
        return self.similar(agent_id, text, limit=limit)

    async def aby_tag(self, agent_id: str, tag: str, limit: int = 5) -> list[MemoryEntry]:
        return self.by_tag(agent_id, tag, limit=limit)

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        start = time.perf_counter()
        self.backend.prune(agent_id, threshold, ttl=ttl)
        MEMORY_OP_COUNT.labels("prune").inc()
        MEMORY_OP_LATENCY.labels("prune").observe(time.perf_counter() - start)

    async def aprune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        self.prune(agent_id, threshold, ttl=ttl)

    def start_pruner(self, agent_id: str, interval: float, ttl: float) -> threading.Thread:
        """Launch a background thread that periodically prunes expired entries."""
        def run() -> None:
            while True:
                time.sleep(interval)
                self.prune(agent_id, ttl=ttl)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t


class ShardedMemoryStore:
    """Memory store that shards data across multiple backends."""

    def __init__(self, backends: Sequence[BaseMemoryBackend] | None = None, shards: int = 1) -> None:
        if backends is None:
            backends = [InMemoryBackend() for _ in range(shards)]
        self.stores = [MemoryStore(b) for b in backends]

    def _store(self, agent_id: str) -> MemoryStore:
        idx = hash(agent_id) % len(self.stores)
        return self.stores[idx]

    def add(self, agent_id: str, text: str, **kw) -> None:
        self._store(agent_id).add(agent_id, text, **kw)

    async def aadd(self, agent_id: str, text: str, **kw) -> None:
        await self._store(agent_id).aadd(agent_id, text, **kw)

    def get(self, agent_id: str, limit: int = 5) -> list[MemoryEntry]:
        return self._store(agent_id).get(agent_id, limit)

    async def aget(self, agent_id: str, limit: int = 5) -> list[MemoryEntry]:
        return await self._store(agent_id).aget(agent_id, limit)

    def search(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        return self._store(agent_id).search(agent_id, query, limit)

    def similar(self, agent_id: str, text: str, limit: int = 5) -> list[MemoryEntry]:
        return self._store(agent_id).similar(agent_id, text, limit)

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> list[MemoryEntry]:
        return self._store(agent_id).by_tag(agent_id, tag, limit)

    async def asearch(self, agent_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        return await self._store(agent_id).asearch(agent_id, query, limit)

    async def asimilar(self, agent_id: str, text: str, limit: int = 5) -> list[MemoryEntry]:
        return await self._store(agent_id).asimilar(agent_id, text, limit)

    async def aby_tag(self, agent_id: str, tag: str, limit: int = 5) -> list[MemoryEntry]:
        return await self._store(agent_id).aby_tag(agent_id, tag, limit)

    def prune(self, agent_id: str, threshold: float = 0.2, ttl: float | None = None) -> None:
        self._store(agent_id).prune(agent_id, threshold, ttl=ttl)

    async def aprune(self, agent_id: str, threshold: float = 0.2, ttl: float | None = None) -> None:
        await self._store(agent_id).aprune(agent_id, threshold, ttl=ttl)

    def start_pruner(self, agent_id: str, interval: float, ttl: float) -> threading.Thread:
        return self._store(agent_id).start_pruner(agent_id, interval, ttl)


@dataclass
class Context:
    """Structured context passed to models."""

    agent_id: str
    prompt: str
    memories: list[MemoryEntry]


class ContextInjector:
    """Injects recent memory into a prompt template."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def inject(self, agent_id: str, prompt: str) -> str:
        memories = await self.store.aget(agent_id)
        context = "\n".join(m.text for m in memories)
        if context:
            return f"{context}\n\n{prompt}"
        return prompt

    async def build_context(self, agent_id: str, prompt: str) -> Context:
        memories = await self.store.aget(agent_id)
        return Context(agent_id=agent_id, prompt=prompt, memories=memories)


@dataclass
class ModelStats:
    name: str
    successes: int = 0
    trials: int = 0

    def record(self, success: bool) -> None:
        self.trials += 1
        if success:
            self.successes += 1


class BanditStrategy:
    """Base interface for bandit algorithms."""

    def select(self, models: dict[str, ModelStats]) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def update(self, models: dict[str, ModelStats], model: str, success: bool) -> None:
        models[model].record(success)


class UCB1Strategy(BanditStrategy):
    def select(self, models: dict[str, ModelStats]) -> str:
        total_trials = sum(m.trials for m in models.values()) or 1
        scores = {}
        for m in models.values():
            if m.trials == 0:
                scores[m.name] = float("inf")
            else:
                avg = m.successes / m.trials
                bonus = sqrt(2 * log(total_trials) / m.trials)
                scores[m.name] = avg + bonus
        return max(scores, key=scores.get)


class ThompsonStrategy(BanditStrategy):
    def select(self, models: dict[str, ModelStats]) -> str:
        scores = {
            m.name: betavariate(m.successes + 1, m.trials - m.successes + 1)
            for m in models.values()
        }
        return max(scores, key=scores.get)


class SoftmaxStrategy(BanditStrategy):
    def __init__(self, temperature: float = 0.5) -> None:
        self.temperature = temperature

    def select(self, models: dict[str, ModelStats]) -> str:
        scores = {}
        for m in models.values():
            if m.trials == 0:
                scores[m.name] = 1.0
            else:
                avg = m.successes / m.trials
                scores[m.name] = pow(2.71828, avg / self.temperature)
        total = sum(scores.values())
        r = random() * total
        upto = 0.0
        for name, score in scores.items():
            upto += score
            if upto >= r:
                return name
        return name  # pragma: no cover - fallback


@dataclass
class Telemetry:
    model: str
    success: bool
    latency: float


ROUTER_LATENCY = Histogram(
    "router_latency_seconds",
    "Latency of router executions",
    ["model", "result"],
)
ROUTER_FAILURES = Counter(
    "router_failures_total",
    "Total router execution failures",
    ["model"],
)


class BanditRouter:
    """Route requests using pluggable bandit algorithms."""

    def __init__(self, models: Sequence[str], strategy: BanditStrategy | str = "ucb1") -> None:
        self.models = {name: ModelStats(name) for name in models}
        if isinstance(strategy, str):
            key = strategy.lower()
            if key == "ucb1":
                self.strategy = UCB1Strategy()
            elif key == "thompson":
                self.strategy = ThompsonStrategy()
            elif key == "softmax":
                self.strategy = SoftmaxStrategy()
            else:
                raise ValueError("Invalid algorithm")
        else:
            self.strategy = strategy
        self.telemetry: list[Telemetry] = []


    def select(self) -> str:
        return self.strategy.select(self.models)

    def record_result(self, model: str, success: bool) -> None:
        self.strategy.update(self.models, model, success)

    async def execute(
        self,
        func: Callable[[str], Awaitable[object]],
        *,
        fallback: Callable[[str], Awaitable[object]] | None = None,
        attempts: int | None = None,
    ) -> object:
        """Run ``func`` with model selection, retry/fallback and telemetry."""
        attempts = attempts or len(self.models)
        last_exc: Exception | None = None
        for _ in range(attempts):
            name = self.select()
            start = time.perf_counter()
            try:
                result = await func(name)
                self.record_result(name, True)
                latency = time.perf_counter() - start
                self.telemetry.append(Telemetry(name, True, latency))
                ROUTER_LATENCY.labels(model=name, result="success").observe(latency)
                return result
            except Exception as exc:
                self.record_result(name, False)
                latency = time.perf_counter() - start
                self.telemetry.append(Telemetry(name, False, latency))
                ROUTER_LATENCY.labels(model=name, result="failure").observe(latency)
                ROUTER_FAILURES.labels(model=name).inc()
                last_exc = exc
                if fallback:
                    start_fb = time.perf_counter()
                    try:
                        result = await fallback(name)
                        self.record_result(name, True)
                        dur_fb = time.perf_counter() - start_fb
                        self.telemetry.append(Telemetry(name, True, dur_fb))
                        ROUTER_LATENCY.labels(model=name, result="fallback").observe(dur_fb)
                        return result
                    except Exception as exc2:
                        ROUTER_LATENCY.labels(model=name, result="fb_fail").observe(
                            time.perf_counter() - start_fb
                        )
                        ROUTER_FAILURES.labels(model=name).inc()
                        last_exc = exc2
                        continue
        if last_exc:
            raise last_exc
        raise RuntimeError("All attempts failed")

