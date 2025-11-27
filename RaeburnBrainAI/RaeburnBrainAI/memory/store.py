"""Lightweight in-memory memory store used by the injector and router tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Sequence


@dataclass
class MemoryEntry:
    text: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)


class MemoryStore:
    def __init__(self) -> None:
        self._memories: Dict[str, List[MemoryEntry]] = {}

    def write(self, agent_id: str, text: str, *, tags: Sequence[str] | None = None, importance: float = 0.5) -> None:
        entry = MemoryEntry(text=text, tags=list(tags or []), importance=importance)
        self._memories.setdefault(agent_id, []).append(entry)

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        return list(self._memories.get(agent_id, []))[-limit:][::-1]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        matches = [m for m in self._memories.get(agent_id, []) if query.lower() in m.text.lower()]
        matches.sort(key=lambda m: m.timestamp, reverse=True)
        return matches[:limit]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        matches = [m for m in self._memories.get(agent_id, []) if tag in m.tags]
        matches.sort(key=lambda m: m.timestamp, reverse=True)
        return matches[:limit]

    def get_relevant(self, agent_id: str, query: str, limit: int = 5, tags: Sequence[str] | None = None) -> List[MemoryEntry]:
        tagged: List[MemoryEntry] = []
        if tags:
            for tag in tags:
                tagged.extend(self.by_tag(agent_id, tag, limit=limit))
        hits = self.search(agent_id, query, limit=limit)
        combined = tagged + hits
        combined.sort(key=lambda m: m.timestamp, reverse=True)
        seen = set()
        deduped: List[MemoryEntry] = []
        for m in combined:
            key = (m.text, tuple(m.tags))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(m)
        return deduped[:limit]
