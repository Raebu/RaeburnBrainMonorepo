from raeburn_brain.core import (
    MemoryStore,
    ShardedMemoryStore,
    ContextInjector,
    BanditRouter,
)
import pytest
import asyncio


def test_memory_store_basic():
    store = MemoryStore()
    store.add("agent", "hello", tags=["greeting"])
    store.add("agent", "world")
    memories = store.get("agent")
    assert len(memories) == 2
    assert memories[0].text == "hello"
    assert memories[0].tags == ["greeting"]

    # search should find entries by tag or text
    hits = store.search("agent", "greeting")
    assert len(hits) == 1 and hits[0].text == "hello"

    # pruning should drop low importance
    store.add("agent", "tmp", importance=0.1)
    store.prune("agent", threshold=0.2)
    ids = [m.text for m in store.get("agent")]
    assert "tmp" not in ids


def test_context_injection():
    store = MemoryStore()
    store.add("a1", "mem1")
    injector = ContextInjector(store)
    result = asyncio.run(injector.inject("a1", "prompt"))
    assert result.startswith("mem1\n\n")


def test_bandit_router_ucb1():
    router = BanditRouter(["m1", "m2"], strategy="ucb1")
    choice = router.select()
    assert choice in {"m1", "m2"}
    router.record_result(choice, True)
    # The unexplored model should be selected next due to infinite UCB score
    other = "m2" if choice == "m1" else "m1"
    assert router.select() == other


def test_bandit_router_thompson():
    router = BanditRouter(["a", "b"], strategy="thompson")
    for _ in range(10):
        name = router.select()
        router.record_result(name, success=True)
    assert sum(m.trials for m in router.models.values()) == 10


def test_bandit_router_softmax():
    router = BanditRouter(["x", "y"], strategy="softmax")
    router.record_result("x", True)
    router.record_result("x", True)
    router.record_result("y", False)
    # x should have higher probability due to successes
    counts = {"x": 0, "y": 0}
    for _ in range(100):
        counts[router.select()] += 1
    assert counts["x"] > counts["y"]


def test_bandit_execute_retry(monkeypatch):
    router = BanditRouter(["fail", "good"], strategy="ucb1")

    async def task(model: str) -> str:
        if model == "fail":
            raise RuntimeError("boom")
        return model

    result = asyncio.run(router.execute(task))
    assert result == "good"
    assert any(t.model == "fail" and not t.success for t in router.telemetry)


@pytest.mark.asyncio
async def test_memory_store_async():
    store = MemoryStore()
    await store.aadd("a", "one")
    items = await store.aget("a")
    assert items and items[0].text == "one"


def test_sharded_memory_store():
    store = ShardedMemoryStore(shards=2)
    store.add("a1", "foo")
    store.add("b2", "bar")
    assert store.get("a1")[0].text == "foo"
    assert store.get("b2")[0].text == "bar"


@pytest.mark.asyncio
async def test_bandit_fallback():
    router = BanditRouter(["remote"], strategy="ucb1")

    async def remote(model: str) -> str:
        raise RuntimeError("fail")

    async def local(model: str) -> str:
        return "local"

    result = await router.execute(remote, fallback=local)
    assert result == "local"

