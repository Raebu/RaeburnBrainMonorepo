import importlib
import json
from agents.identity_engine import get_agent_by_role, list_agents, register_agent, reload_agents
from agents import identity_engine
from agents.decision_engine import build_prompt


def test_get_agent_unknown_returns_generalist():
    agent = get_agent_by_role("unknown")
    assert agent["name"] == "generalist"


def test_load_agents_from_env(tmp_path, monkeypatch):
    cfg = tmp_path / "agents.json"
    cfg.write_text(json.dumps({"analyst": {"name": "analyst"}}))
    monkeypatch.setenv("RAEBURN_AGENT_CONFIG", str(cfg))
    importlib.reload(identity_engine)
    agent = identity_engine.get_agent_by_role("analyst")
    assert agent["name"] == "analyst"
    assert "analyst" in identity_engine.list_agents()


def test_load_agents_invalid_config(tmp_path, monkeypatch):
    cfg = tmp_path / "agents.json"
    # invalid because name is not a string
    cfg.write_text(json.dumps({"bad": {"name": 123}}))
    monkeypatch.setenv("RAEBURN_AGENT_CONFIG", str(cfg))
    importlib.reload(identity_engine)
    assert "bad" not in identity_engine.list_agents()


def test_build_prompt_includes_system_and_style():
    agent = {"name": "tester", "system_prompt": "SYS", "prompt_style": "casual"}
    prompt = build_prompt(agent, "hello", ["prev answer"])
    assert "SYS" in prompt
    assert "Style: casual" in prompt
    assert "User: hello" in prompt


def test_build_prompt_without_context_or_style():
    agent = {"name": "plain"}
    prompt = build_prompt(agent, "go", [])
    assert "Context" not in prompt
    assert "Style:" not in prompt
    assert prompt.startswith("User: go")


def test_list_agents_default():
    roles = list_agents()
    assert "generalist" in roles
    assert "copywriter" in roles


def test_dynamic_agent_registration():
    reload_agents()
    register_agent(
        "planner",
        system_prompt="Plan tasks",
        capabilities=["plan"],
        model_preferences=["openai"],
    )
    agent = get_agent_by_role("planner")
    assert agent["capabilities"] == ["plan"]
    assert agent["model_preferences"] == ["openai"]
