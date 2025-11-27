import asyncio
import pytest
from core.memory_store import MemoryStore
from core.memory_injector import inject_memories


@pytest.mark.asyncio
async def test_memory_store_search(tmp_path):
    log = tmp_path / "mem.log"
    store = MemoryStore(path=str(log))
    await store.save_memory({"input": "foo", "output": "bar"})
    await store.save_memory({"input": "foo baz", "output": "qux"})
    results = await store.search_memories("foo", limit=2)
    assert len(results) == 2
    assert results[0].output == "qux"
    assert results[1].output == "bar"


@pytest.mark.asyncio
async def test_inject_memories_limit(monkeypatch, tmp_path):
    log = tmp_path / "mem.log"
    monkeypatch.setenv("RAEBURN_MEMORY_PATH", str(log))
    monkeypatch.setenv("RAEBURN_ORCHESTRATOR_MEMORY_LIMIT", "1")
    store = MemoryStore(path=str(log))
    await store.save_memory({"input": "foo", "output": "first"})
    await store.save_memory({"input": "foo", "output": "second"})
    context = await inject_memories("foo", {"name": "tester"})
    assert context == ["second"]



@pytest.mark.asyncio
async def test_search_memories_skips_bad_lines(tmp_path):
    log = tmp_path / "mem.log"
    log.write_text('{"input": "hi", "output": "ok"}\nINVALID\n')
    store = MemoryStore(path=str(log))
    results = await store.search_memories("hi", limit=2)
    assert len(results) == 1
    assert results[0].output == "ok"


@pytest.mark.asyncio
async def test_save_memory_failure_logs(monkeypatch, tmp_path):
    store = MemoryStore(path=tmp_path / "m.log")

    def boom(*args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("aiofiles.open", boom)
    events = []
    async def capture(e, d):
        events.append((e, d))

    monkeypatch.setattr("core.memory_store.log_event", capture)
    with pytest.raises(OSError):
        await store.save_memory({"input": "x"})
    assert events and events[0][0] == "memory_error"


@pytest.mark.asyncio
async def test_search_memories_failure_logs(monkeypatch, tmp_path):
    store = MemoryStore(path=tmp_path / "m.log")

    def boom(*args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("aiofiles.open", boom)
    events = []
    async def capture2(e, d):
        events.append((e, d))

    monkeypatch.setattr("core.memory_store.log_event", capture2)
    store.path.write_text("")
    with pytest.raises(OSError):
        await store.search_memories("x")
    assert events and events[0][0] == "memory_error"


@pytest.mark.asyncio
async def test_memory_store_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "mem.db"
    monkeypatch.setenv("RAEBURN_DB_PATH", str(db))
    store = MemoryStore(db_path=str(db))
    await store.save_memory({"input": "foo", "output": "bar"})
    await store.save_memory({"input": "foo", "output": "baz"})
    results = await store.search_memories("foo")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_memory_store_concurrent(tmp_path):
    db = tmp_path / "mem.db"
    store = MemoryStore(db_path=str(db))

    async def save(text):
        await store.save_memory({"input": text, "output": text})

    await asyncio.gather(save("a"), save("b"))
    results = await store.search_memories("a")
    assert any(r.output == "a" for r in results)


@pytest.mark.asyncio
async def test_memory_store_postgres(monkeypatch):
    class FakeConn:
        def __init__(self) -> None:
            self.rows: list[str] = []

        async def execute(self, *args):
            if args[0].startswith("INSERT"):
                self.rows.append(args[-1])

        async def fetch(self, *args):
            return [{"json": self.rows[0]}] if self.rows else []

        async def close(self) -> None:  # pragma: no cover
            pass

    conn = FakeConn()

    class FakePool:
        def __init__(self, c) -> None:
            self.c = c
            self.calls = 0

        class Acquire:
            def __init__(self, pool):
                self.pool = pool
            async def __aenter__(self):
                self.pool.calls += 1
                return self.pool.c
            async def __aexit__(self, exc_type, exc, tb):
                pass

        def acquire(self):
            return FakePool.Acquire(self)

        async def release(self, _c) -> None:  # pragma: no cover
            pass

    pool = FakePool(conn)

    called: dict[str, int] = {}

    async def create_pool(url, min_size=1, max_size=10):
        called["min_size"] = min_size
        called["max_size"] = max_size
        return pool

    monkeypatch.setenv("RAEBURN_DB_URL", "postgresql://")
    monkeypatch.setenv("RAEBURN_PG_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("RAEBURN_PG_POOL_MAX_SIZE", "5")
    monkeypatch.setattr("asyncpg.create_pool", create_pool)
    store = MemoryStore(db_url="postgresql://")
    await store.save_memory({"input": "x", "output": "y"})
    results = await store.search_memories("x")
    assert results and results[0].output == "y"
    assert pool.calls >= 2
    assert called["min_size"] == 2
    assert called["max_size"] == 5
