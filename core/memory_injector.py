from .memory_store import MemoryStore
import os

async def inject_memories(user_input: str, agent: dict):
    """Retrieve relevant memories for the prompt."""
    limit = int(os.getenv("RAEBURN_ORCHESTRATOR_MEMORY_LIMIT", "5"))
    store = MemoryStore()
    matches = await store.search_memories(user_input, limit=limit)
    return [getattr(m, "output", "") for m in matches]
