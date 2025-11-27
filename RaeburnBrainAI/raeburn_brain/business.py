from __future__ import annotations

"""Business Factory for creating business agents and tracking KPIs."""

from typing import Iterable, Sequence
from dataclasses import dataclass
import sqlite3

from .agent import AgentRegistry
from .core import MemoryStore


class BusinessMetricsStore:
    """Persist business KPI metrics to SQLite."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS metrics (biz_id TEXT, role TEXT, kpi REAL)"
        )
        self.conn.commit()

    def record(self, biz_id: str, role: str, kpi: float) -> None:
        self.conn.execute(
            "INSERT INTO metrics (biz_id, role, kpi) VALUES (?, ?, ?)",
            (biz_id, role, kpi),
        )
        self.conn.commit()

    def average(self, biz_id: str, role: str) -> float:
        cur = self.conn.execute(
            "SELECT AVG(kpi) FROM metrics WHERE biz_id = ? AND role = ?",
            (biz_id, role),
        )
        row = cur.fetchone()
        return row[0] or 0.0


@dataclass
class Business:
    biz_id: str
    roles: Sequence[str]


class BusinessFactory:
    """Create business agents and adjust their roles based on KPIs."""

    def __init__(
        self,
        registry: AgentRegistry,
        store: MemoryStore,
        metrics: BusinessMetricsStore | None = None,
        threshold: float = 0.5,
    ) -> None:
        self.registry = registry
        self.store = store
        self.metrics = metrics or BusinessMetricsStore()
        self.threshold = threshold

    def create_business(self, biz_id: str, roles: Iterable[str]) -> Business:
        role_list = list(roles)
        for role in role_list:
            agent_id = f"{biz_id}-{role}"
            self.registry.ensure(agent_id, [role])
            self.store.add(agent_id, f"init memory for {role}", tags=[biz_id, role])
        return Business(biz_id=biz_id, roles=role_list)

    def record_kpi(self, biz_id: str, role: str, value: float) -> None:
        self.metrics.record(biz_id, role, value)
        avg = self.metrics.average(biz_id, role)
        agent_id = f"{biz_id}-{role}"
        self.registry.record(agent_id, avg >= self.threshold)

    def agents(self, biz_id: str) -> list[str]:
        return [a.id for a in self.registry.list() if a.id.startswith(f"{biz_id}-")]


__all__ = ["BusinessMetricsStore", "Business", "BusinessFactory"]
