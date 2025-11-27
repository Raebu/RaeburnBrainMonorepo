from RaeburnBrainAI.memory import MemoryStore, MemoryInjector


def test_memory_injector_orders_and_filters():
    store = MemoryStore()
    store.write("agent1", "older note", tags=["general"], importance=0.1)
    store.write("agent1", "recent tag match", tags=["task"], importance=0.9)
    injector = MemoryInjector(store, limit=3)
    context = injector.inject_context("agent1", "task details", tags=["task"])
    assert "recent tag match" in context
    assert "older note" in context
    # recent tag appears before older note
    assert context.index("recent tag match") < context.index("older note")
