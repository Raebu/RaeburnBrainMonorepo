from __future__ import annotations

"""Memory and knowledge layer with pluggable backends."""

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence
import time
import json
import threading
import numpy as np
from prometheus_client import Counter, Histogram

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional
    faiss = None

import sqlite3
from tinydb import TinyDB, Query

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency
    psycopg = None

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - optional dependency
    Vector = None

MEMORY_OP_COUNT = Counter(
    "memory_operations_total",
    "Total memory store operations",
    ["op"],
)
MEMORY_OP_LATENCY = Histogram(
    "memory_operation_seconds",
    "Time spent in memory store operations",
    ["op"],
)


def _default_embed(text: str, dims: int) -> np.ndarray:
    """Return a deterministic embedding vector for ``text``."""
    import hashlib

    h = hashlib.sha256(text.encode()).digest()
    rng = np.frombuffer(h, dtype=np.uint8)
    rng = np.resize(rng, dims).astype("float32")
    return rng / 255.0


@dataclass
class MemoryEntry:
    """Single memory item with semantic tags and importance."""

    text: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: float = field(default_factory=lambda: time.time())


class BaseMemoryBackend:
    """Abstract base class for memory backends."""

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        raise NotImplementedError

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        raise NotImplementedError

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        raise NotImplementedError

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        """Return entries semantically similar to ``text``."""
        raise NotImplementedError

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        raise NotImplementedError

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        """Return recent entries containing ``tag``."""
        raise NotImplementedError


class InMemoryBackend(BaseMemoryBackend):
    """Simple in-memory backend used for tests and defaults."""

    def __init__(self, embed: callable | None = None, dims: int = 64) -> None:
        self._store: dict[str, List[MemoryEntry]] = {}
        self._embed = embed or _default_embed
        self._dims = dims
        self._vectors: dict[str, np.ndarray] = {}

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        entry = MemoryEntry(text=text, tags=list(tags), importance=importance)
        self._store.setdefault(agent_id, []).append(entry)
        vec = self._embed(text, self._dims).astype("float32")
        self._vectors.setdefault(agent_id, np.empty((0, self._dims), dtype="float32"))
        self._vectors[agent_id] = np.vstack([self._vectors[agent_id], vec])

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        return list(self._store.get(agent_id, []))[-limit:]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        results = [
            e
            for e in self._store.get(agent_id, [])
            if query.lower() in e.text.lower() or query in e.tags
        ]
        return results[-limit:]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        entries = [e for e in self._store.get(agent_id, []) if tag in e.tags]
        return entries[-limit:]

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        vec = self._embed(text, self._dims).astype("float32")
        matrix = self._vectors.get(agent_id)
        if matrix is None or not len(matrix):
            return []
        dists = np.linalg.norm(matrix - vec, axis=1)
        idxs = np.argsort(dists)[:limit]
        return [self._store[agent_id][i] for i in idxs]

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        now = time.time()
        items = [
            e
            for e in self._store.get(agent_id, [])
            if e.importance >= threshold and (ttl is None or now - e.timestamp <= ttl)
        ]
        if items:
            self._store[agent_id] = items
            self._vectors[agent_id] = self._vectors[agent_id][-len(items):]
        else:
            self._store.pop(agent_id, None)
            self._vectors.pop(agent_id, None)


class TinyDBBackend(BaseMemoryBackend):
    """TinyDB based memory backend with simple substring search."""

    def __init__(self, path: str = "memory.json") -> None:
        self.db = TinyDB(path)
        self.table = self.db.table("entries")

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        self.table.insert(
            {
                "agent_id": agent_id,
                "text": text,
                "tags": list(tags),
                "importance": importance,
                "timestamp": time.time(),
            }
        )

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        q = Query()
        rows = self.table.search(q.agent_id == agent_id)[-limit:]
        return [MemoryEntry(r["text"], r["tags"], r["importance"], r.get("timestamp", time.time())) for r in rows]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        q = Query()
        rows = self.table.search(
            (q.agent_id == agent_id)
            & ((q.text.test(lambda v: query.lower() in v.lower())) | (q.tags.any(query)))
        )[-limit:]
        return [MemoryEntry(r["text"], r["tags"], r["importance"], r.get("timestamp", time.time())) for r in rows]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        q = Query()
        rows = self.table.search((q.agent_id == agent_id) & (q.tags.any(tag)))[-limit:]
        return [MemoryEntry(r["text"], r["tags"], r["importance"], r.get("timestamp", time.time())) for r in rows]

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        return self.search(agent_id, text, limit)

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        q = Query()
        cond = (q.agent_id == agent_id) & (q.importance < threshold)
        if ttl is not None:
            cutoff = time.time() - ttl
            cond |= (q.agent_id == agent_id) & (q.timestamp < cutoff)
        self.table.remove(cond)


class SQLiteBackend(BaseMemoryBackend):
    """SQLite backend using FTS5 for full-text search."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS entries USING fts5(agent_id, text, tags, importance UNINDEXED, timestamp UNINDEXED)"
        )
        self.conn.commit()

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        tags_str = ",".join(tags)
        self.conn.execute(
            "INSERT INTO entries (agent_id, text, tags, importance, timestamp) VALUES (?, ?, ?, ?, ?)",
            (agent_id, text, tags_str, importance, time.time()),
        )
        self.conn.commit()

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        cur = self.conn.execute(
            "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = ? ORDER BY rowid DESC LIMIT ?",
            (agent_id, limit),
        )
        rows = cur.fetchall()
        return [MemoryEntry(r[0], r[1].split(",") if r[1] else [], r[2], r[3]) for r in rows]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        cur = self.conn.execute(
            "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = ? AND entries MATCH ? ORDER BY rank LIMIT ?",
            (agent_id, query, limit),
        )
        rows = cur.fetchall()
        return [MemoryEntry(r[0], r[1].split(",") if r[1] else [], r[2], r[3]) for r in rows]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        cur = self.conn.execute(
            "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = ? AND tags LIKE ? ORDER BY rowid DESC LIMIT ?",
            (agent_id, f"%{tag}%", limit),
        )
        rows = cur.fetchall()
        return [MemoryEntry(r[0], r[1].split(",") if r[1] else [], r[2], r[3]) for r in rows]

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        return self.search(agent_id, text, limit)

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        query = "DELETE FROM entries WHERE agent_id = ? AND importance < ?"
        params: list = [agent_id, threshold]
        if ttl is not None:
            query += " OR (agent_id = ? AND timestamp < ?)"
            params.extend([agent_id, time.time() - ttl])
        self.conn.execute(query, params)
        self.conn.commit()


class PostgresBackend(BaseMemoryBackend):
    """PostgreSQL backend using tsvector for search."""

    def __init__(self, dsn: str) -> None:
        if psycopg is None:
            raise ImportError("psycopg is required for PostgresBackend")
        self.conn = psycopg.connect(dsn)
        # assume table created via Alembic migration

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO entries (agent_id, text, tags, importance, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (agent_id, text, list(tags), importance, time.time()),
            )
        self.conn.commit()

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = %s ORDER BY id DESC LIMIT %s",
                (agent_id, limit),
            )
            rows = cur.fetchall()
        return [MemoryEntry(r[0], list(r[1] or []), r[2], r[3]) for r in rows]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = %s AND %s = ANY(tags) ORDER BY id DESC LIMIT %s",
                (agent_id, tag, limit),
            )
            rows = cur.fetchall()
        return [MemoryEntry(r[0], list(r[1] or []), r[2], r[3]) for r in rows]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = %s AND search @@ plainto_tsquery(%s) ORDER BY id DESC LIMIT %s",
                (agent_id, query, limit),
            )
            rows = cur.fetchall()
        return [MemoryEntry(r[0], list(r[1] or []), r[2], r[3]) for r in rows]

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        return self.search(agent_id, text, limit)

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        with self.conn.cursor() as cur:
            query = "DELETE FROM entries WHERE agent_id = %s AND importance < %s"
            params = [agent_id, threshold]
            if ttl is not None:
                query += " OR (agent_id = %s AND timestamp < %s)"
                params.extend([agent_id, time.time() - ttl])
            cur.execute(query, params)
        self.conn.commit()


class FaissBackend(BaseMemoryBackend):
    """FAISS-powered backend for semantic search."""

    def __init__(self, dims: int = 64, embed: callable | None = None) -> None:
        if faiss is None:
            raise ImportError("faiss-cpu is required for FaissBackend")
        self.dims = dims
        self._embed = embed or _default_embed
        self._store: dict[str, List[MemoryEntry]] = {}
        self._index: dict[str, faiss.IndexFlatL2] = {}

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        entry = MemoryEntry(text=text, tags=list(tags), importance=importance)
        self._store.setdefault(agent_id, []).append(entry)
        vec = self._embed(text, self.dims).astype("float32").reshape(1, -1)
        index = self._index.setdefault(agent_id, faiss.IndexFlatL2(self.dims))
        index.add(vec)

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        return list(self._store.get(agent_id, []))[-limit:]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        return [e for e in self._store.get(agent_id, []) if query.lower() in e.text.lower()][:limit]

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        index = self._index.get(agent_id)
        if index is None or index.ntotal == 0:
            return []
        vec = self._embed(text, self.dims).astype("float32").reshape(1, -1)
        dists, idx = index.search(vec, limit)
        entries = self._store.get(agent_id, [])
        return [entries[i] for i in idx[0] if i < len(entries)]

    def prune(self, agent_id: str, threshold: float = 0.2, *, ttl: float | None = None) -> None:
        now = time.time()
        entries = self._store.get(agent_id, [])
        index = self._index.get(agent_id)
        if not entries or index is None:
            return
        keep = []
        vectors = []
        for i, e in enumerate(entries):
            if e.importance >= threshold and (ttl is None or now - e.timestamp <= ttl):
                keep.append(e)
                vectors.append(index.reconstruct(i))
        if keep:
            self._store[agent_id] = keep
            new_index = faiss.IndexFlatL2(self.dims)
            if vectors:
                new_index.add(np.vstack(vectors))
            self._index[agent_id] = new_index
        else:
            self._store.pop(agent_id, None)
            self._index.pop(agent_id, None)

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        return [e for e in self._store.get(agent_id, []) if tag in e.tags][-limit:]


class PgvectorBackend(PostgresBackend):
    """PostgreSQL backend using pgvector for vector search."""

    def __init__(self, dsn: str, dims: int = 64, embed: callable | None = None) -> None:
        if Vector is None:
            raise ImportError("pgvector is required for PgvectorBackend")
        self.dims = dims
        self._embed = embed or _default_embed
        super().__init__(dsn)
        # embedding column assumed to exist via migration

    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] = (),
        importance: float = 0.5,
    ) -> None:
        vec = self._embed(text, self.dims).tolist()
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO entries (agent_id, text, tags, importance, embedding, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
                (agent_id, text, list(tags), importance, vec, time.time()),
            )
        self.conn.commit()

    def similar(self, agent_id: str, text: str, limit: int = 5) -> List[MemoryEntry]:
        vec = self._embed(text, self.dims).tolist()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT text, tags, importance, timestamp FROM entries WHERE agent_id = %s ORDER BY embedding <-> %s LIMIT %s",
                (agent_id, vec, limit),
            )
            rows = cur.fetchall()
        return [MemoryEntry(r[0], list(r[1] or []), r[2], r[3]) for r in rows]


def ingest_logs(store: "MemoryStore", path: str, agent_id: str) -> int:
    """Ingest memory entries from a log file (JSON or plain text)."""
    count = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                text = obj.get("text") or obj.get("message") or line
                tags = obj.get("tags", [])
                importance = obj.get("importance", 0.5)
            except Exception:
                text = line
                tags = []
                importance = 0.5
            store.add(agent_id, text, tags=tags, importance=importance)
            count += 1
    return count


__all__ = [
    "MemoryEntry",
    "BaseMemoryBackend",
    "InMemoryBackend",
    "TinyDBBackend",
    "SQLiteBackend",
    "PostgresBackend",
    "FaissBackend",
    "PgvectorBackend",
    "ingest_logs",
]
