import pytest
from fastapi.testclient import TestClient
from raeburn_brain.orchestrator.api import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_MEMORY_PATH", str(tmp_path / "mem.log"))
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path))
    monkeypatch.setenv("RAEBURN_ORCHESTRATOR_MODE", "test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return TestClient(app)


def test_orchestrate_endpoint(client):
    resp = client.post("/orchestrate", json={"user_input": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert data["session_id"]


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
