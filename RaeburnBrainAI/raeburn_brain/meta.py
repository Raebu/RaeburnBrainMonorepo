# Meta-agent scheduler for Raeburn Brain AI
from __future__ import annotations

"""Meta agent scheduler and mission tracking."""

import asyncio
import time
import sqlite3
from dataclasses import dataclass

from .agent import AgentRegistry
from .core import MemoryStore
from .model import ModelMetricsStore


class MissionOutcomeStore:
    """Persist mission results for later analysis."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS missions (agent_id TEXT, mission TEXT, success INTEGER, ts REAL)"
        )
        self.conn.commit()

    def record(self, agent_id: str, mission: str, success: bool) -> None:
        self.conn.execute(
            "INSERT INTO missions (agent_id, mission, success, ts) VALUES (?, ?, ?, ?)",
            (agent_id, mission, int(success), time.time()),
        )
        self.conn.commit()

    def list(self, agent_id: str) -> list[tuple[str, bool, float]]:
        cur = self.conn.execute(
            "SELECT mission, success, ts FROM missions WHERE agent_id = ?",
            (agent_id,),
        )
        return [(m, bool(s), ts) for m, s, ts in cur.fetchall()]


@dataclass
class Mission:
    """Simple mission description assigned to an agent."""

    agent_id: str
    text: str


class MetaAgentScheduler:
    """Generate daily missions and evaluate agent performance."""

    def __init__(
        self,
        registry: AgentRegistry,
        store: MemoryStore,
        metrics: ModelMetricsStore | None = None,
        *,
        outcomes: MissionOutcomeStore | None = None,
        interval: float = 86_400,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.registry = registry
        self.store = store
        self.metrics = metrics
        self.outcomes = outcomes or MissionOutcomeStore()
        self.interval = interval
        if loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        else:
            self._loop = loop
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background scheduler task."""
        if self._task and not self._task.done():
            return
        self._task = self._loop.create_task(self._run())

    def stop(self) -> None:
        """Stop the scheduler task."""
        if self._task:
            self._task.cancel()
            try:
                self._loop.run_until_complete(self._task)
            except Exception:
                pass
            self._task = None

    # internal helpers -----------------------------------------------------
    async def _run(self) -> None:
        while True:
            self.perform_daily()
            await asyncio.sleep(self.interval)

    def perform_daily(self) -> None:
        """Assign missions and evaluate all agents."""
        for agent in self.registry.list():
            mission = self.generate_mission(agent.id)
            self.store.add(agent.id, mission, tags=["mission"], importance=0.7)
            success = self.evaluate_agent(agent.id)
            self.outcomes.record(agent.id, mission, success)

    def generate_mission(self, agent_id: str) -> str:
        """Return a trivial mission string for now."""
        return f"Daily mission for {agent_id}"

    def evaluate_agent(self, agent_id: str) -> bool:
        """Update agent score based on logs and metrics."""
        success_logs = len(self.store.search(agent_id, "success"))
        fail_logs = len(self.store.search(agent_id, "fail")) + len(
            self.store.search(agent_id, "error")
        )
        success = success_logs >= fail_logs
        if self.metrics:
            rows = list(self.metrics.all())
            if rows:
                avg_latency = sum(r[1] for r in rows) / len(rows)
                if avg_latency > 1.0:
                    success = False
        self.registry.record(agent_id, success)
        return success


__all__ = ["Mission", "MissionOutcomeStore", "MetaAgentScheduler"]
