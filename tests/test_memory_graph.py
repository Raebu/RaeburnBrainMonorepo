import os
import pytest
import numpy as np
import asyncio
from raeburnmemory.memory_graph import MemoryGraph, faiss, Prompt, Response, Agent

pytestmark = pytest.mark.requires("numpy")


def test_add_and_retrieve(tmp_path):
    db = tmp_path / "graph.json"
    mg = MemoryGraph(db_path=str(db), embedding_model=None)
    mg.add_interaction(
        prompt={"id": "p1", "text": "How do I make vegan pancakes?"},
        response={"id": "r1", "text": "Here's a recipe..."},
        agent={"id": "agent1", "name": "ChefAI"},
        session_id="sess1",
    )
    mg.export()
    mg2 = MemoryGraph(db_path=str(db), embedding_model=None)
    results = mg2.get_similar_prompts("Pancake recipe?")
    assert "p1" in results
    assert mg2.vector_index.ntotal == 1


def test_visualise_chain(tmp_path):
    mg = MemoryGraph(db_path=str(tmp_path / "g.json"), embedding_model=None)
    # Build a small chain manually
    mg.graph.add_node("p1")
    mg.graph.add_node("r1")
    mg.graph.add_node("p2")
    mg.graph.add_node("r2")
    mg.graph.add_edge("p1", "r1")
    mg.graph.add_edge("r1", "p2")
    mg.graph.add_edge("p2", "r2")
    chain = mg.visualise_prompt_chain("p1", depth=3)
    assert chain == [("p1", "r1"), ("r1", "p2"), ("p2", "r2")]


def test_link_similar_prompts(tmp_path):
    class TinyModel:
        def encode(self, texts):
            vecs = []
            for t in texts:
                if t.endswith("1"):
                    vecs.append(np.array([1.0, 0.0], dtype=np.float32))
                else:
                    vecs.append(np.array([0.9, 0.0], dtype=np.float32))
            return vecs

    class SmallMG(MemoryGraph):
        def _init_vector_index(self):
            return faiss.IndexFlatL2(2)

    mg = SmallMG(db_path=str(tmp_path / "g2.json"), embedding_model=None)
    mg.model = TinyModel()
    mg.add_interaction(
        prompt={"id": "p1", "text": "text1"},
        response={"id": "r1", "text": "resp1"},
        agent={"id": "a1", "name": "A"},
        session_id="s",
    )
    mg.add_interaction(
        prompt={"id": "p2", "text": "text2"},
        response={"id": "r2", "text": "resp2"},
        agent={"id": "a1", "name": "A"},
        session_id="s",
    )
    mg.link_similar_prompts(threshold=0.8)
    assert ("p1", "p2") in mg.graph.edges or ("p2", "p1") in mg.graph.edges


def _add_in_process(db, idx):
    mg = MemoryGraph(db_path=db, embedding_model=None)
    mg.add_interaction(
        prompt={"id": f"p{idx}", "text": f"text{idx}"},
        response={"id": f"r{idx}", "text": "resp"},
        agent={"id": "a", "name": "A"},
        session_id="s",
    )
    mg.export()


def test_concurrent_access(tmp_path):
    db = str(tmp_path / "concurrent.json")
    from multiprocessing import Process

    procs = [Process(target=_add_in_process, args=(db, i)) for i in range(5)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    mg = MemoryGraph(db_path=db, embedding_model=None)
    prompt_nodes = [n for n, d in mg.graph.nodes.items() if d.get("type") == "prompt"]
    assert len(prompt_nodes) >= 1


def test_sqlite_backend(tmp_path):
    db = tmp_path / "graph.db"
    mg = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    mg.add_interaction(
        prompt={"id": "p1", "text": "hi"},
        response={"id": "r1", "text": "hello"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    mg2 = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    assert "p1" in mg2.get_similar_prompts("hi")


def test_migrate_json(tmp_path):
    json_path = tmp_path / "old.json"
    mg = MemoryGraph(db_path=str(json_path), embedding_model=None)
    mg.add_interaction(
        prompt={"id": "p1", "text": "hi"},
        response={"id": "r1", "text": "hello"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    mg.export()
    db = tmp_path / "old.db"
    mg2 = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    assert "p1" in mg2.get_similar_prompts("hi")


def test_migrate_without_vectors(tmp_path):
    json_path = tmp_path / "plain.json"
    mg = MemoryGraph(db_path=str(json_path), embedding_model=None)
    mg.graph.add_node("p1", type="prompt", text="hi")
    mg.graph.add_node("r1", type="response", text="hello")
    mg.graph.add_edge("p1", "r1", relation="responded_with")
    mg.export()
    assert not os.path.exists(str(json_path) + ".vectors.npy")
    assert not os.path.exists(str(json_path) + ".faiss")
    db = tmp_path / "plain.db"
    mg2 = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    mg2.close()
    mg3 = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    assert "p1" in mg3.graph.nodes


def test_load_missing_file(tmp_path):
    mg = MemoryGraph(db_path=str(tmp_path / "missing.json"), embedding_model=None)
    assert len(mg.graph.nodes) == 0


def test_load_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{invalid")
    mg = MemoryGraph(db_path=str(path), embedding_model=None)
    assert len(mg.graph.nodes) == 0


def test_load_corrupted_sqlite(tmp_path):
    path = tmp_path / "bad.db"
    path.write_bytes(b"corrupted")
    mg = MemoryGraph(db_path=str(path), embedding_model=None, storage_backend="sqlite")
    assert len(mg.graph.nodes) == 0


def test_faiss_fallback(monkeypatch, tmp_path):
    import builtins
    import importlib

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "faiss":
            raise ImportError
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import raeburnmemory.memory_graph as mg_module

    mg_module = importlib.reload(mg_module)
    index = mg_module.MemoryGraph(
        db_path=str(tmp_path / "f.json"), embedding_model=None
    ).vector_index
    assert hasattr(index, "vectors")


def test_networkx_fallback(monkeypatch, tmp_path):
    import builtins
    import importlib

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "networkx":
            raise ImportError
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import raeburnmemory.memory_graph as mg_module

    mg_module = importlib.reload(mg_module)
    assert mg_module.nx.__name__ == "nx"
    mg = mg_module.MemoryGraph(db_path=str(tmp_path / "n.json"), embedding_model=None)
    assert isinstance(mg.graph, mg_module.nx.DiGraph)


def _add_sqlite(db, idx):
    mg = MemoryGraph(db_path=db, embedding_model=None, storage_backend="sqlite")
    mg.add_interaction(
        prompt={"id": f"p{idx}", "text": f"text{idx}"},
        response={"id": f"r{idx}", "text": "resp"},
        agent={"id": "a", "name": "A"},
        session_id="s",
    )


def test_concurrent_sqlite_access(tmp_path):
    db = str(tmp_path / "concurrent.db")
    from multiprocessing import Process

    procs = [Process(target=_add_sqlite, args=(db, i)) for i in range(5)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    mg = MemoryGraph(db_path=db, embedding_model=None, storage_backend="sqlite")
    prompt_nodes = [n for n, d in mg.graph.nodes.items() if d.get("type") == "prompt"]
    assert len(prompt_nodes) == 5


def test_sqlite_threaded_reads_and_writes(tmp_path):
    db = str(tmp_path / "threaded.db")

    def writer(i):
        g = MemoryGraph(db_path=db, embedding_model=None, storage_backend="sqlite")
        g.add_interaction(
            prompt={"id": f"tp{i}", "text": f"t{i}"},
            response={"id": f"tr{i}", "text": "resp"},
            agent={"id": "a", "name": "A"},
            session_id="s",
        )

    def reader():
        g = MemoryGraph(db_path=db, embedding_model=None, storage_backend="sqlite")
        g.export(path=False)

    from threading import Thread

    threads = [Thread(target=writer, args=(i,)) for i in range(3)] + [
        Thread(target=reader) for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    mg = MemoryGraph(db_path=db, embedding_model=None, storage_backend="sqlite")
    prompts = [n for n, d in mg.graph.nodes.items() if d.get("type") == "prompt"]
    assert len(prompts) == 3


def test_close_method(tmp_path):
    db = tmp_path / "close.db"
    mg = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    mg.add_interaction(
        prompt={"id": "p1", "text": "hi"},
        response={"id": "r1", "text": "there"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    mg.close()
    assert mg._conn is None
    mg2 = MemoryGraph(db_path=str(db), embedding_model=None, storage_backend="sqlite")
    assert "p1" in mg2.graph.nodes


def test_faiss_index_persistence(tmp_path):
    path = tmp_path / "persist.json"
    mg = MemoryGraph(db_path=str(path), embedding_model=None)
    mg.add_interaction(
        prompt={"id": "p1", "text": "hello"},
        response={"id": "r1", "text": "hi"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    mg.export()
    faiss_file = path.with_suffix(path.suffix + ".faiss")
    vec_file = path.with_suffix(path.suffix + ".vectors.npy")
    assert faiss_file.exists() or vec_file.exists()
    mg2 = MemoryGraph(db_path=str(path), embedding_model=None)
    assert "p1" in mg2.get_similar_prompts("hello")


def test_async_batch(tmp_path):
    db = tmp_path / "async.json"
    mg = MemoryGraph(db_path=str(db), embedding_model=None)
    interactions = [
        (
            Prompt(id=f"p{i}", text="hi"),
            Response(id=f"r{i}", text="ho"),
            Agent(id="a", name="A"),
            "s",
        )
        for i in range(3)
    ]
    asyncio.run(mg.batch_add(interactions))
    assert mg.vector_index.ntotal == 3 or mg.vector_backend == "qdrant"


@pytest.mark.requires("qdrant_client")
def test_qdrant_backend(tmp_path):
    db = tmp_path / "q.json"
    mg = MemoryGraph(db_path=str(db), embedding_model=None, vector_backend="qdrant")
    mg.add_interaction(
        prompt={"id": "p1", "text": "hello"},
        response={"id": "r1", "text": "hi"},
        agent={"id": "a1", "name": "bot"},
        session_id="s",
    )
    ids = mg.get_similar_prompts("hello")
    assert "p1" in ids
