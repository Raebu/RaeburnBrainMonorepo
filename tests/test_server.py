import importlib
import logging

from raeburn_brain.server import create_app, configure_logging
from fastapi.testclient import TestClient


def test_observability_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("RAEBURN_DASHBOARD_TOKEN", "tok")
    monkeypatch.setenv("RAEBURN_OAUTH_USER", "user")
    monkeypatch.setenv("RAEBURN_OAUTH_PASS", "pass")
    monkeypatch.setenv("RAEBURN_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    import raeburn_brain.agent as agent_mod
    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(agent_mod)
    monkeypatch.setenv("RAEBURN_LOG_AGENT", "srv")
    store = configure_logging()
    app = create_app(store)
    client = TestClient(app)

    login = client.post("/token", data={"username": "user", "password": "pass"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # unauthorized without credentials
    assert client.get("/healthz").status_code == 401

    r = client.get("/healthz", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/uptime", headers=headers)
    assert r.status_code == 200
    assert "uptime_seconds" in r.json()

    r = client.get("/metrics", headers=headers)
    assert r.status_code == 200
    assert "app_requests_total" in r.text

    r = client.get("/dashboard", headers=headers)
    assert r.status_code == 200
    assert "Agent Metrics" in r.text

    # agent endpoints
    r = client.post("/agents", json={"id": "a1", "traits": ["nice"]}, headers=headers)
    assert r.status_code == 200
    r = client.post("/agents/a1/mentor", json={"mentor_id": "a1"}, headers=headers)
    assert r.status_code == 200
    r = client.post("/agents/a1/clone", json={"new_id": "clone"}, headers=headers)
    assert r.status_code == 200

    logging.getLogger().info("hello")

