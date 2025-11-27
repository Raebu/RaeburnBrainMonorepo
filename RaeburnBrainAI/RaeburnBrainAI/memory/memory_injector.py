"""Memory injector that formats relevant memories for prompts."""

from __future__ import annotations

from typing import List, Sequence

from RaeburnBrainAI.memory.store import MemoryStore, MemoryEntry


class MemoryInjector:
    def __init__(self, store: MemoryStore, limit: int = 5) -> None:
        self.store = store
        self.limit = limit

    def inject_context(self, agent_id: str, prompt: str, *, tags: Sequence[str] | None = None) -> str:
        memories = self.store.get_relevant(agent_id, prompt, limit=self.limit, tags=tags)
        block = "\n".join(f"- {m.text}" for m in memories)
        if block:
            return f"Context:\n{block}\n\nPrompt: {prompt}"
        return prompt

    def fetch(self, agent_id: str, *, tags: Sequence[str] | None = None) -> List[MemoryEntry]:
        return self.store.get_relevant(agent_id, "", limit=self.limit, tags=tags)
