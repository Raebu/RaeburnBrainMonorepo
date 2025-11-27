
"""Persistent, sharded memory store with TTL, tags, FTS, blob refs, and maintenance helpers.

This is the central long-term memory engine for RaeburnBrainAI/BusinessFactory.
It supports:
- Sharded SQLite backends (per agent/business + global)
- TTL expiry and importance pruning/decay
- Tag filtering + FTS5 keyword search
- Hybrid scoring (BM25 + recency + importance)
- Blob references for large binary payloads
- Integrity checks, orphan blob cleanup, soft deletes
- Optional Postgres backend (JSONB + tsvector) with optional embeddings

Vector/pg integrations are optional; if MEMORY_DB_URL is set and asyncpg is available,
Postgres will be used for read/write paths.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable, List, Sequence

try:  # optional postgres
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover
    asyncpg = None  # type: ignore

try:  # optional embeddings
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

# Environment-driven configuration
MEMORY_PATH = Path(os.getenv("MEMORY_PATH", "memory"))
MEMORY_SHARDING = os.getenv("MEMORY_SHARDING", "true").lower() == "true"
MEMORY_TTL_DEFAULT = float(os.getenv("MEMORY_TTL_DEFAULT", "0")) or None
MEMORY_MAX_RESULTS = int(os.getenv("MEMORY_MAX_RESULTS", "5"))
MEMORY_QUERY_STRICT = os.getenv("MEMORY_QUERY_STRICT", "false").lower() == "true"
MEMORY_IMPORTANCE_DECAY = os.getenv("MEMORY_IMPORTANCE_DECAY", "false").lower() == "true"
MEMORY_DECAY_FACTOR = float(os.getenv("MEMORY_DECAY_FACTOR", "0.98"))  # applied per decay pass
MEMORY_EMBEDDINGS_ENABLED = os.getenv("MEMORY_EMBEDDINGS_ENABLED", "false").lower() == "true"
MEMORY_DB_URL = os.getenv("MEMORY_DB_URL")  # optional Postgres path (pgvector recommended)

SHARDS_DIR = MEMORY_PATH / "shards"
BLOBS_DIR = MEMORY_PATH / "blobs"
GLOBAL_DB = MEMORY_PATH / "global.db"

_pg_pool: Any | None = None
_pg_lock = asyncio.Lock()
_embed_model: Any | None = None


@dataclass
class MemoryItem:
    id: str
    agent_id: str
    text: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    blob_ref: str | None = None
    deleted: bool = False
    embedding: list[float] | None = None


class MemoryStore:
    def __init__(self, shard: str | None = None) -> None:
        self.shard = shard  # e.g., agent_<id>, business_<id>, or None for global
        SHARDS_DIR.mkdir(parents=True, exist_ok=True)
        BLOBS_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_PATH.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ---------- Shard helpers ----------
    def _db_path(self) -> Path:
        if MEMORY_SHARDING and self.shard:
            return SHARDS_DIR / f"{self.shard}.db"
        return GLOBAL_DB

    def for_agent(self, agent_id: str) -> "MemoryStore":
        return MemoryStore(shard=f"agent_{agent_id}")

    def for_business(self, biz_id: str) -> "MemoryStore":
        return MemoryStore(shard=f"business_{biz_id}")

    # ---------- Embeddings ----------
    def _embed(self, text: str) -> list[float] | None:
        if not MEMORY_EMBEDDINGS_ENABLED or SentenceTransformer is None:
            return None
        global _embed_model
        if _embed_model is None:
            model_name = os.getenv("MEMORY_EMBED_MODEL", "all-MiniLM-L6-v2")
            _embed_model = SentenceTransformer(model_name)
        vec = _embed_model.encode(text)
        return vec.tolist() if hasattr(vec, "tolist") else list(vec)

    # ---------- SQLite schema ----------
    def _connect(self) -> sqlite3.Connection:
        path = self._db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        self._ensure_schema(conn)
        return conn

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_entries ("
            "id TEXT PRIMARY KEY,"
            "agent_id TEXT,"
            "text TEXT,"
            "tags TEXT,"
            "importance REAL,"
            "created_at REAL,"
            "expires_at REAL,"
            "source TEXT,"
            "metadata TEXT,"
            "blob_ref TEXT,"
            "deleted INTEGER DEFAULT 0,"
            "embedding TEXT"
            ")"
        )
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS fts_entries USING fts5(text, content='memory_entries', content_rowid='rowid')"
        )
        conn.execute(
            "CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries "
            "BEGIN INSERT INTO fts_entries(rowid, text) VALUES (new.rowid, new.text); END;"
        )
        # Ensure new columns exist on older DBs
        for column in ("deleted", "embedding"):
            try:
                conn.execute(f"ALTER TABLE memory_entries ADD COLUMN {column} TEXT")
            except Exception:
                pass
        conn.commit()

    def _purge_expired(self, conn: sqlite3.Connection) -> None:
        now = time.time()
        conn.execute("DELETE FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
        conn.commit()

    # ---------- Postgres helpers ----------
    async def _pg_pool(self):
        global _pg_pool
        if _pg_pool is not None:
            return _pg_pool
        if asyncpg is None or not MEMORY_DB_URL:
            return None
        async with _pg_lock:
            if _pg_pool is None:
                _pg_pool = await asyncpg.create_pool(MEMORY_DB_URL, min_size=1, max_size=5)
                async with _pg_pool.acquire() as conn:
                    await conn.execute(
                        "CREATE TABLE IF NOT EXISTS memory_entries ("
                        "id UUID PRIMARY KEY,"
                        "agent_id TEXT,"
                        "text TEXT,"
                        "tags JSONB,"
                        "importance DOUBLE PRECISION,"
                        "created_at DOUBLE PRECISION,"
                        "expires_at DOUBLE PRECISION,"
                        "source TEXT,"
                        "metadata JSONB,"
                        "blob_ref TEXT,"
                        "deleted BOOLEAN DEFAULT FALSE,"
                        "embedding JSONB"
                        ")"
                    )
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent ON memory_entries(agent_id)")
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_deleted ON memory_entries(deleted)")
        return _pg_pool

    def _run_async(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        return asyncio.run(coro)

    # ---------- Blob helpers ----------
    def write_blob(self, data: bytes) -> str:
        blob_id = f"{uuid.uuid4()}.bin"
        dest = BLOBS_DIR / blob_id
        dest.write_bytes(data)
        return str(dest)

    def read_blob(self, blob_ref: str) -> bytes:
        return Path(blob_ref).read_bytes()

    def delete_blob(self, blob_ref: str) -> None:
        try:
            Path(blob_ref).unlink(missing_ok=True)
        except Exception:
            pass

    def cleanup_orphan_blobs(self) -> None:
        """Remove blobs not referenced by any memory entry."""
        conn = self._connect()
        cur = conn.execute("SELECT blob_ref FROM memory_entries WHERE blob_ref IS NOT NULL")
        refs = {Path(r[0]).name for r in cur.fetchall() if r[0]}
        conn.close()
        for blob_path in BLOBS_DIR.glob("*.bin"):
            if blob_path.name not in refs:
                blob_path.unlink(missing_ok=True)

    # ---------- Core operations ----------
    def add(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] | None = None,
        importance: float = 0.5,
        ttl: float | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        blob: bytes | None = None,
    ) -> MemoryItem:
        entry_id = str(uuid.uuid4())
        expires_at = time.time() + ttl if ttl else (MEMORY_TTL_DEFAULT + time.time() if MEMORY_TTL_DEFAULT else None)
        blob_ref = self.write_blob(blob) if blob is not None else None
        embedding = self._embed(text)
        entry = MemoryItem(
            id=entry_id,
            agent_id=agent_id,
            text=text,
            tags=list(tags or []),
            importance=importance,
            created_at=time.time(),
            expires_at=expires_at,
            source=source,
            metadata=metadata or {},
            blob_ref=blob_ref,
            deleted=False,
            embedding=embedding,
        )
        if MEMORY_DB_URL and asyncpg is not None:
            self._run_async(self._add_pg(entry))
            return entry
        with self._lock:
            conn = self._connect()
            self._purge_expired(conn)
            conn.execute(
                "INSERT INTO memory_entries (id, agent_id, text, tags, importance, created_at, expires_at, source, metadata, blob_ref, deleted, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (
                    entry.id,
                    entry.agent_id,
                    entry.text,
                    json.dumps(entry.tags),
                    entry.importance,
                    entry.created_at,
                    entry.expires_at,
                    entry.source,
                    json.dumps(entry.metadata),
                    entry.blob_ref,
                    json.dumps(entry.embedding) if entry.embedding is not None else None,
                ),
            )
            conn.commit()
            conn.close()
        return entry

    async def _add_pg(self, entry: MemoryItem) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO memory_entries (id, agent_id, text, tags, importance, created_at, expires_at, source, metadata, blob_ref, deleted, embedding) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",
                entry.id,
                entry.agent_id,
                entry.text,
                entry.tags,
                entry.importance,
                entry.created_at,
                entry.expires_at,
                entry.source,
                entry.metadata,
                entry.blob_ref,
                entry.deleted,
                entry.embedding,
            )

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryItem:
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except Exception:
            tags = []
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except Exception:
            metadata = {}
        try:
            embedding = json.loads(row["embedding"]) if row["embedding"] else None
        except Exception:
            embedding = None
        return MemoryItem(
            id=row["id"],
            agent_id=row["agent_id"],
            text=row["text"],
            tags=tags,
            importance=row["importance"] or 0.0,
            created_at=row["created_at"] or time.time(),
            expires_at=row["expires_at"],
            source=row["source"],
            metadata=metadata,
            blob_ref=row["blob_ref"],
            deleted=bool(row["deleted"]),
            embedding=embedding,
        )

    async def _row_to_entry_pg(self, row: Any) -> MemoryItem:
        return MemoryItem(
            id=str(row["id"]),
            agent_id=row["agent_id"],
            text=row["text"],
            tags=list(row.get("tags") or []),
            importance=float(row.get("importance") or 0.0),
            created_at=float(row.get("created_at") or time.time()),
            expires_at=float(row.get("expires_at")) if row.get("expires_at") is not None else None,
            source=row.get("source"),
            metadata=dict(row.get("metadata") or {}),
            blob_ref=row.get("blob_ref"),
            deleted=bool(row.get("deleted", False)),
            embedding=list(row.get("embedding") or []) or None,
        )

    def get(self, agent_id: str, limit: int | None = None, include_deleted: bool = False) -> List[MemoryItem]:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._get_pg(agent_id, limit, include_deleted))
        limit = limit or MEMORY_MAX_RESULTS
        conn = self._connect()
        self._purge_expired(conn)
        where = "agent_id = ?" + ("" if include_deleted else " AND deleted = 0")
        cur = conn.execute(
            f"SELECT * FROM memory_entries WHERE {where} ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [self._row_to_entry(r) for r in rows]

    async def _get_pg(self, agent_id: str, limit: int | None, include_deleted: bool) -> List[MemoryItem]:
        pool = await self._pg_pool()
        if pool is None:
            return []
        limit = limit or MEMORY_MAX_RESULTS
        deleted_clause = "" if include_deleted else "AND deleted = FALSE"
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM memory_entries WHERE agent_id = $1 {deleted_clause} ORDER BY created_at DESC LIMIT $2",
                agent_id,
                limit,
            )
        return [await self._row_to_entry_pg(r) for r in rows]

    def search(
        self,
        agent_id: str,
        query: str,
        limit: int | None = None,
        tags: Sequence[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> List[MemoryItem]:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._search_pg(agent_id, query, limit, tags, metadata_filter))
        limit = limit or MEMORY_MAX_RESULTS
        conn = self._connect()
        self._purge_expired(conn)
        clauses = ["agent_id = ?", "deleted = 0"]
        params: list[Any] = [agent_id]
        if tags and MEMORY_QUERY_STRICT:
            clauses.append("tags = ?")
            params.append(json.dumps(list(tags)))
        if metadata_filter:
            for key, val in metadata_filter.items():
                clauses.append("metadata LIKE ?")
                params.append(f"%"{key}"%{val}%")
        where = " AND ".join(clauses)
        cur = conn.execute(
            f"SELECT e.*, bm25(fts_entries) as bm25_score FROM fts_entries JOIN memory_entries e ON fts_entries.rowid = e.rowid "
            f"WHERE fts_entries MATCH ? AND {where} ORDER BY bm25_score ASC, created_at DESC LIMIT ?",
            (query, *params, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [self._row_to_entry(r) for r in rows]

    async def _search_pg(
        self,
        agent_id: str,
        query: str,
        limit: int | None,
        tags: Sequence[str] | None,
        metadata_filter: dict[str, Any] | None,
    ) -> List[MemoryItem]:
        pool = await self._pg_pool()
        if pool is None:
            return []
        limit = limit or MEMORY_MAX_RESULTS
        clauses = ["agent_id = $1", "deleted = FALSE"]
        params: list[Any] = [agent_id]
        if tags and MEMORY_QUERY_STRICT:
            clauses.append("tags = $2")
            params.append(list(tags))
        where = " AND ".join(clauses)
        query_sql = (
            f"SELECT *, ts_rank_cd(to_tsvector('english', text), plainto_tsquery('english', ${{len(params)+1}})) as rank "
            f"FROM memory_entries WHERE {where} AND to_tsvector('english', text) @@ plainto_tsquery('english', ${{len(params)+1}}) "
            f"ORDER BY rank DESC, created_at DESC LIMIT ${{len(params)+2}}"
        )
        params.append(query)
        params.append(limit)
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(query_sql, *params)
            except Exception:
                rows = await conn.fetch(
                    f"SELECT * FROM memory_entries WHERE {where} AND text ILIKE ${{len(params)+1}} ORDER BY created_at DESC LIMIT ${{len(params)+2}}",
                    *params[:-2],
                    f"%{query}%",
                    limit,
                )
        return [await self._row_to_entry_pg(r) for r in rows]

    def get_relevant(
        self,
        agent_id: str,
        query: str,
        *,
        tags: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> List[MemoryItem]:
        limit = limit or MEMORY_MAX_RESULTS
        candidates = self.search(agent_id, query, limit=limit * 3, tags=tags) if query else self.get(agent_id, limit=limit * 3)
        now = time.time()
        scored: list[tuple[float, MemoryItem]] = []
        for entry in candidates:
            if entry.deleted:
                continue
            recency = 1.0 / (1.0 + (now - entry.created_at) / 3600.0)
            importance = entry.importance or 0.0
            bm25_score = 1.0
            scored.append((bm25_score * 0.5 + recency * 0.3 + importance * 0.2, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def update(
        self,
        entry_id: str,
        *,
        text: str | None = None,
        tags: Sequence[str] | None = None,
        ttl: float | None = None,
        metadata: dict[str, Any] | None = None,
        importance: float | None = None,
    ) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._update_pg(entry_id, text, tags, ttl, metadata, importance))
        conn = self._connect()
        self._purge_expired(conn)
        cur = conn.execute("SELECT * FROM memory_entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        entry = self._row_to_entry(row)
        if text is not None:
            entry.text = text
        if tags is not None:
            entry.tags = list(tags)
        if ttl is not None:
            entry.expires_at = time.time() + ttl
        if metadata is not None:
            entry.metadata = metadata
        if importance is not None:
            entry.importance = importance
        conn.execute(
            "UPDATE memory_entries SET text = ?, tags = ?, importance = ?, expires_at = ?, metadata = ? WHERE id = ?",
            (
                entry.text,
                json.dumps(entry.tags),
                entry.importance,
                entry.expires_at,
                json.dumps(entry.metadata),
                entry.id,
            ),
        )
        conn.commit()
        conn.close()

    async def _update_pg(
        self,
        entry_id: str,
        text: str | None,
        tags: Sequence[str] | None,
        ttl: float | None,
        metadata: dict[str, Any] | None,
        importance: float | None,
    ) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memory_entries WHERE id = $1", entry_id)
            if not row:
                return
            entry = await self._row_to_entry_pg(row)
            if text is not None:
                entry.text = text
            if tags is not None:
                entry.tags = list(tags)
            if ttl is not None:
                entry.expires_at = time.time() + ttl
            if metadata is not None:
                entry.metadata = metadata
            if importance is not None:
                entry.importance = importance
            await conn.execute(
                "UPDATE memory_entries SET text = $1, tags = $2, importance = $3, expires_at = $4, metadata = $5 WHERE id = $6",
                entry.text,
                entry.tags,
                entry.importance,
                entry.expires_at,
                entry.metadata,
                entry.id,
            )

    def soft_delete(self, entry_id: str) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._soft_delete_pg(entry_id))
        conn = self._connect()
        conn.execute("UPDATE memory_entries SET deleted = 1 WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()

    async def _soft_delete_pg(self, entry_id: str) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute("UPDATE memory_entries SET deleted = TRUE WHERE id = $1", entry_id)

    def delete(self, entry_id: str) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._delete_pg(entry_id))
        conn = self._connect()
        conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()

    async def _delete_pg(self, entry_id: str) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_entries WHERE id = $1", entry_id)

    def prune_expired(self) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            self._run_async(self._prune_expired_pg())
            return
        conn = self._connect()
        self._purge_expired(conn)
        conn.execute("VACUUM")
        conn.close()

    async def _prune_expired_pg(self) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        now = time.time()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at < $1", now)

    def prune_importance(self, threshold: float = 0.2) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._prune_importance_pg(threshold))
        conn = self._connect()
        conn.execute("DELETE FROM memory_entries WHERE importance < ?", (threshold,))
        conn.commit()
        conn.close()

    async def _prune_importance_pg(self, threshold: float) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_entries WHERE importance < $1", threshold)

    def apply_importance_decay(self) -> None:
        if not MEMORY_IMPORTANCE_DECAY:
            return
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._decay_pg())
        conn = self._connect()
        conn.execute("UPDATE memory_entries SET importance = importance * ?", (MEMORY_DECAY_FACTOR,))
        conn.commit()
        conn.close()

    async def _decay_pg(self) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute("UPDATE memory_entries SET importance = importance * $1", MEMORY_DECAY_FACTOR)

    def integrity_check(self) -> bool:
        conn = self._connect()
        cur = conn.execute("PRAGMA integrity_check")
        rows = cur.fetchall()
        conn.close()
        return all(r[0] == "ok" for r in rows)

    def dump_all(self) -> List[dict[str, Any]]:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._dump_pg())
        conn = self._connect()
        cur = conn.execute("SELECT * FROM memory_entries")
        rows = cur.fetchall()
        conn.close()
        return [asdict(self._row_to_entry(r)) for r in rows]

    async def _dump_pg(self) -> List[dict[str, Any]]:
        pool = await self._pg_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM memory_entries")
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(asdict(await self._row_to_entry_pg(r)))
        return out

    def load_dump(self, items: Iterable[dict[str, Any]]) -> None:
        if MEMORY_DB_URL and asyncpg is not None:
            return self._run_async(self._load_pg(items))
        conn = self._connect()
        self._purge_expired(conn)
        for item in items:
            conn.execute(
                "INSERT OR REPLACE INTO memory_entries (id, agent_id, text, tags, importance, created_at, expires_at, source, metadata, blob_ref, deleted, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.get("id", str(uuid.uuid4())),
                    item.get("agent_id", "global"),
                    item.get("text", ""),
                    json.dumps(item.get("tags") or []),
                    item.get("importance", 0.0),
                    item.get("created_at", time.time()),
                    item.get("expires_at"),
                    item.get("source"),
                    json.dumps(item.get("metadata") or {}),
                    item.get("blob_ref"),
                    int(item.get("deleted", False)),
                    json.dumps(item.get("embedding")) if item.get("embedding") is not None else None,
                ),
            )
        conn.commit()
        conn.close()

    async def _load_pg(self, items: Iterable[dict[str, Any]]) -> None:
        pool = await self._pg_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            async with conn.transaction():
                for item in items:
                    await conn.execute(
                        "INSERT INTO memory_entries (id, agent_id, text, tags, importance, created_at, expires_at, source, metadata, blob_ref, deleted, embedding) "
                        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) "
                        "ON CONFLICT (id) DO UPDATE SET text=EXCLUDED.text, tags=EXCLUDED.tags, importance=EXCLUDED.importance,"
                        " created_at=EXCLUDED.created_at, expires_at=EXCLUDED.expires_at, source=EXCLUDED.source, metadata=EXCLUDED.metadata,"
                        " blob_ref=EXCLUDED.blob_ref, deleted=EXCLUDED.deleted, embedding=EXCLUDED.embedding",
                        item.get("id", str(uuid.uuid4())),
                        item.get("agent_id", "global"),
                        item.get("text", ""),
                        item.get("tags") or [],
                        item.get("importance", 0.0),
                        item.get("created_at", time.time()),
                        item.get("expires_at"),
                        item.get("source"),
                        item.get("metadata") or {},
                        item.get("blob_ref"),
                        bool(item.get("deleted", False)),
                        item.get("embedding"),
                    )

    # ---------- Embedding hooks (semantic search placeholder) ----------
    def embed_text(self, text: str) -> list[float]:
        vec = self._embed(text)
        if vec is None:
            raise NotImplementedError("Embeddings disabled or backend not available")
        return vec

    def semantic_search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        # Placeholder: implement with pgvector/FAISS; returning empty for now
        return []


__all__ = ["MemoryStore", "MemoryItem"]
