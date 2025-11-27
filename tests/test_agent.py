import importlib

from raeburn_brain.agent import generate_persona
from raeburn_brain.db import run_migrations


def test_generate_persona():
    persona = generate_persona(["brave", "curious"])
    assert "brave" in persona and "curious" in persona


def test_agent_lifecycle(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path}/agents.db"
    monkeypatch.setenv("RAEBURN_DATABASE_URL", db_url)
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    import raeburn_brain.agent as agent_mod
    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(agent_mod)
    run_migrations()
    from raeburn_brain.agent import AgentRegistry
    reg = AgentRegistry()
    reg.ensure("a1", ["smart"])
    for _ in range(5):
        reg.record("a1", True)
    assert reg.get("a1").title == "promoted"
    # Now fail repeatedly to trigger sandbox
    for _ in range(20):
        reg.record("a1", False)
    assert reg.get("a1").sandboxed is True

    reg.ensure("mentor", ["wise"])
    reg.mentor("a1", "mentor")
    clone = reg.clone("a1", "a2")
    assert clone.mentor_id == "a1"

    reg2 = AgentRegistry()
    assert reg2.get("a1").sandboxed is True

