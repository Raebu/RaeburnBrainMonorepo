import os

# ruff: noqa: E402

os.environ["RAEBURN_API_KEY"] = "secret"
os.environ["RAEBURN_RATE_LIMIT"] = "0"
import pytest
from fastapi.testclient import TestClient
import raeburnmemory.api as api
from raeburnmemory.memory_graph import MemoryGraph

pytestmark = pytest.mark.requires("fastapi")


def override_graph(path):
    mg = MemoryGraph(db_path=path, embedding_model=None)

    def _dep():
        return mg

    return mg, _dep


def reset_api(api_module):
    api_module.app.dependency_overrides.clear()
    try:
        api_module.RATE_LIMIT_CALLS.clear()
    except Exception:
        pass


def test_get_graph(tmp_path):
    graph, dep = override_graph(str(tmp_path / "g.json"))
    graph.add_interaction(
        prompt={"id": "p1", "text": "Hello"},
        response={"id": "r1", "text": "Hi"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)
    resp = client.get("/memory/graph", headers={"Authorization": "Bearer secret"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [n["id"] for n in data["nodes"]]
    assert "p1" in ids
    reset_api(api)


def test_post_similar(tmp_path):
    graph, dep = override_graph(str(tmp_path / "g2.json"))
    graph.add_interaction(
        prompt={"id": "p1", "text": "foo"},
        response={"id": "r1", "text": "bar"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)
    resp = client.post(
        "/memory/similar",
        json={"text": "foo"},
        headers={"Authorization": "Bearer secret"},
    )
    assert resp.status_code == 200
    assert "p1" in resp.json()["ids"]
    reset_api(api)


def test_concurrent_requests(tmp_path):
    graph, dep = override_graph(str(tmp_path / "g3.json"))
    graph.add_interaction(
        prompt={"id": "p1", "text": "foo"},
        response={"id": "r1", "text": "bar"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)

    def call():
        return client.post(
            "/memory/similar",
            json={"text": "foo"},
            headers={"Authorization": "Bearer secret"},
        ).json()

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(lambda _: call(), range(5)))

    assert all("p1" in r["ids"] for r in results)
    reset_api(api)


def test_similar_missing_field(tmp_path):
    mg, dep = override_graph(str(tmp_path / "none.json"))
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)
    resp = client.post(
        "/memory/similar", json={}, headers={"Authorization": "Bearer secret"}
    )
    assert resp.status_code == 400
    assert "text field required" in resp.text
    reset_api(api)


def test_similar_no_embeddings(tmp_path):
    mg, dep = override_graph(str(tmp_path / "empty.json"))
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)
    resp = client.post(
        "/memory/similar",
        json={"text": "hi"},
        headers={"Authorization": "Bearer secret"},
    )
    assert resp.status_code == 404
    reset_api(api)


def test_auth_required(tmp_path):
    mg, dep = override_graph(str(tmp_path / "auth.json"))
    api.app.dependency_overrides[api.get_memory_graph] = dep
    client = TestClient(api.app)
    resp = client.get("/memory/graph")
    assert resp.status_code == 401
    reset_api(api)


def test_rate_limit(tmp_path):
    os.environ["RAEBURN_RATE_LIMIT"] = "2"
    import importlib
    import raeburnmemory.api as api_mod

    api_mod = importlib.reload(api_mod)
    mg, dep = override_graph(str(tmp_path / "rl.json"))
    api_mod.app.dependency_overrides[api_mod.get_memory_graph] = dep
    client = TestClient(api_mod.app)
    headers = {"Authorization": "Bearer secret"}
    for _ in range(2):
        assert client.get("/memory/graph", headers=headers).status_code == 200
    resp = client.get("/memory/graph", headers=headers)
    assert resp.status_code == 429
    reset_api(api_mod)
    os.environ["RAEBURN_RATE_LIMIT"] = "0"
