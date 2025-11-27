from raeburn_brain.memory import (
    TinyDBBackend,
    SQLiteBackend,
    FaissBackend,
    ingest_logs,
)
from raeburn_brain.core import MemoryStore


def test_tinydb_backend(tmp_path):
    path = tmp_path / "mem.json"
    store = MemoryStore(TinyDBBackend(str(path)))
    store.add("a", "hello world", tags=["test"], importance=0.9)
    store.add("a", "bye", importance=0.1)
    results = store.search("a", "hello")
    assert results and results[0].text == "hello world"
    by_tag = store.by_tag("a", "test")
    assert by_tag and by_tag[0].text == "hello world"
    store.prune("a", 0.5)
    remaining = [m.text for m in store.get("a")]
    assert "bye" not in remaining


def test_sqlite_backend(tmp_path):
    db = tmp_path / "mem.db"
    store = MemoryStore(SQLiteBackend(str(db)))
    store.add("b", "foo bar", tags=["x"], importance=1.0)
    store.add("b", "bar baz", importance=0.1)
    assert store.search("b", "foo")
    assert store.by_tag("b", "x")
    store.prune("b", 0.5)
    texts = [e.text for e in store.get("b")]
    assert "bar baz" not in texts


def test_memory_ingest_and_similar(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("{\"text\": \"hello world\", \"tags\": [\"log\"]}\nbye\n")
    store = MemoryStore()
    ingest_logs(store, str(log), agent_id="c")
    assert store.search("c", "hello")
    assert store.by_tag("c", "log")
    sim = store.similar("c", "hello world")
    assert sim and sim[0].text == "hello world"


def test_faiss_backend():
    try:
        store = MemoryStore(FaissBackend())
    except ImportError:
        return  # optional dependency not installed
    store.add("d", "alpha bravo", importance=0.9)
    store.add("d", "charlie", importance=0.5)
    near = store.similar("d", "alpha bravo")
    assert near and near[0].text == "alpha bravo"


def test_memory_migration(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path}/migrate.db"
    monkeypatch.setenv("RAEBURN_DATABASE_URL", db_url)
    import importlib
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    importlib.reload(config)
    importlib.reload(db)
    from raeburn_brain.db import run_migrations, SessionLocal
    run_migrations()
    # verify entries table exists
    from sqlalchemy import text
    with SessionLocal() as sess:
        sess.execute(text("SELECT 1 FROM entries LIMIT 1"))
