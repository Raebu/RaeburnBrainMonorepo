from __future__ import annotations

import importlib

from raeburn_brain.meta import MetaAgentScheduler, MissionOutcomeStore
from raeburn_brain.agent import AgentRegistry
from raeburn_brain.core import MemoryStore
from raeburn_brain.model import ModelMetricsStore
from raeburn_brain.db import run_migrations


def test_meta_scheduler(tmp_path, monkeypatch):
    monkeypatch.setenv('RAEBURN_DATABASE_URL', f'sqlite:///{tmp_path}/agents.db')
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    import raeburn_brain.agent as agent_mod
    import raeburn_brain.meta as meta_mod
    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(agent_mod)
    importlib.reload(meta_mod)
    run_migrations()
    registry = AgentRegistry()
    registry.ensure('a1', ['smart'])
    store = MemoryStore()
    metrics = ModelMetricsStore(tmp_path / 'metrics.db')
    outcomes = MissionOutcomeStore(tmp_path / 'missions.db')
    scheduler = MetaAgentScheduler(registry, store, metrics=metrics, outcomes=outcomes, interval=0.1)
    store.add('a1', 'success', tags=['success'])
    metrics.record('m', 0.5, 0.0)
    scheduler.perform_daily()
    assert registry.get('a1').trials == 1
    assert store.search('a1', 'mission')
    assert outcomes.list('a1')
