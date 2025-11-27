import time

from RaeburnBrainAI.memory.store import MemoryStore


def test_memory_store_write_get_and_search():
    store = MemoryStore()
    store.wipe("agent-test")
    store.write("agent-test", "hello world", tags=["greeting"], importance=0.9)
    assert store.get("agent-test")
    search = store.search("agent-test", "hello")
    assert search and "hello" in search[0].text


def test_memory_store_ttl_expiry():
    store = MemoryStore()
    store.wipe("agent-ttl")
    store.write("agent-ttl", "short lived", ttl=0)
    time.sleep(0.01)
    result = store.get("agent-ttl")
    assert not result
