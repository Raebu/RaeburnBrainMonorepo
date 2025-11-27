from __future__ import annotations

import importlib

from raeburn_brain.business import BusinessFactory, BusinessMetricsStore
from raeburn_brain.agent import AgentRegistry
from raeburn_brain.core import MemoryStore
from raeburn_brain.db import run_migrations


def test_business_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("RAEBURN_DATABASE_URL", f"sqlite:///{tmp_path}/agents.db")
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    import raeburn_brain.agent as agent_mod
    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(agent_mod)
    run_migrations()
    registry = AgentRegistry()
    factory = BusinessFactory(registry, MemoryStore(), BusinessMetricsStore(tmp_path / "kpi.db"))
    factory.create_business("biz", ["marketing"])
    for _ in range(5):
        factory.record_kpi("biz", "marketing", 1.0)
    agent = registry.get("biz-marketing")
    assert agent.title == "promoted"
    assert factory.agents("biz") == ["biz-marketing"]
