import asyncio
import json
import pytest

from raeburn_brain.orchestrator.orchestrator import run_orchestration_pipeline
from raeburn_brain.orchestrator.task import Task


def test_orchestration_flow_basic():
    task = {"user_input": "Summarize the top 3 AI trends today."}
    result = asyncio.run(run_orchestration_pipeline(task))
    assert "result" in result
    assert "model_used" in result
    assert result["score"] >= 0
    assert result["duration_ms"] >= 0
    assert result["priority"] == 1


def test_orchestration_with_dataclass(monkeypatch):
    async def no_log(*a, **k):
        pass

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.log_event", no_log
    )
    task = Task(user_input="hi")
    result = asyncio.run(run_orchestration_pipeline(task))
    assert result["agent"] == "generalist"


def test_env_mode_dry_run(monkeypatch):
    monkeypatch.setenv("RAEBURN_ORCHESTRATOR_MODE", "dry-run")
    task = {"user_input": "Test env var"}
    result = asyncio.run(run_orchestration_pipeline(task))
    assert result["mode"] == "dry-run"




def test_orchestration_saves_memory(tmp_path, monkeypatch):
    mem = tmp_path / "mem.log"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_MEMORY_PATH", str(mem))
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path / "ologs"))
    monkeypatch.setenv("RAEBURN_ORCHESTRATOR_MODE", "prod")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    async def no_log(*a, **k):
        pass

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.log_event",
        no_log,
    )
    result = asyncio.run(run_orchestration_pipeline({"user_input": "hello", "priority": 2}))
    assert mem.exists()
    data = [json.loads(x) for x in mem.read_text().splitlines()]
    assert data[0]["input"] == "hello"
    assert data[0]["priority"] == 2
    assert result["result"] == data[0]["output"]
    qlog = tmp_path / "ologs" / "quality.log"
    assert qlog.exists()
    qdata = json.loads(qlog.read_text().splitlines()[-1])
    assert qdata["session"] == result["session_id"]
    assert qdata["model"] == result["model_used"]


def test_orchestration_uses_db(tmp_path, monkeypatch):
    db = tmp_path / "store.db"
    monkeypatch.setenv("RAEBURN_DB_PATH", str(db))
    monkeypatch.setenv("RAEBURN_ORCHESTRATOR_MODE", "prod")
    async def no_log(*a, **k):
        pass

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.log_event", no_log
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    asyncio.run(run_orchestration_pipeline({"user_input": "hi"}))
    import sqlite3
    conn = sqlite3.connect(db)
    mem = conn.execute("SELECT json FROM memories").fetchone()[0]
    conn.close()
    data = json.loads(mem)
    assert data["input"] == "hi"


def test_orchestration_logs_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("fail")
    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.route_prompt", boom
    )
    events = []
    async def capture(e, d):
        events.append((e, d))

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.log_event",
        capture,
    )
    with pytest.raises(RuntimeError):
        asyncio.run(run_orchestration_pipeline({"user_input": "x"}))
    assert any(ev[0] == "orchestration_error" for ev in events)


def test_priority_enables_parallel(monkeypatch):
    captured = {}

    async def fake_route(prompt, agent, session_id, parallel=False, priority=1):
        captured['parallel'] = parallel
        return [{"id": "a", "content": "hi", "model": "m", "latency": 1, "error": None}]

    async def fake_judge(candidates, user_input):
        return candidates[0], {"a": 1.0}

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.route_prompt",
        fake_route,
    )
    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.judge_outputs",
        fake_judge,
    )
    async def no_save(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.MemoryStore.save_memory",
        no_save,
    )
    async def no_quality(*args, **kwargs):
        pass

    async def no_log(*a, **k):
        pass

    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.record_quality",
        no_quality,
    )
    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.log_event",
        no_log,
    )

    asyncio.run(run_orchestration_pipeline({"user_input": "x", "priority": 2}))
    assert captured.get('parallel') is True


def test_orchestrator_tracing(monkeypatch):
    calls = []

    class DummySpan:
        async def __aenter__(self):
            calls.append("enter")
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummyTracer:
        def start_as_current_span(self, name, **attrs):
            calls.append(name)
            return DummySpan()

    tracer = DummyTracer()
    monkeypatch.setattr(
        "raeburn_brain.orchestrator.orchestrator.tracer",
        tracer,
    )
    monkeypatch.setattr("core.router.tracer", tracer)

    async def fake_route(prompt, agent, session_id, parallel=False, priority=1):
        return [{"id": "a", "content": "hi", "model": "m", "latency": 1, "error": None}]

    async def fake_judge(cands, ui):
        return cands[0], {"a": 1.0}

    async def noop(*a, **k):
        pass

    monkeypatch.setattr("raeburn_brain.orchestrator.orchestrator.route_prompt", fake_route)
    monkeypatch.setattr("raeburn_brain.orchestrator.orchestrator.judge_outputs", fake_judge)
    monkeypatch.setattr("raeburn_brain.orchestrator.orchestrator.MemoryStore.save_memory", noop)
    monkeypatch.setattr("raeburn_brain.orchestrator.orchestrator.log_event", noop)
    monkeypatch.setattr("raeburn_brain.orchestrator.orchestrator.record_quality", noop)

    asyncio.run(run_orchestration_pipeline({"user_input": "hello"}))
    assert "orchestration" in calls
    assert "route_prompt" in calls
