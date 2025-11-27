from __future__ import annotations

import json
import os
import asyncio
from typing import Any, TYPE_CHECKING
from uuid import uuid4

import aiofiles  # type: ignore
import aiosqlite  # type: ignore
import asyncpg  # type: ignore
from utils.logging import log_event
from .memory_record import MemoryRecord

try:  # optional qdrant dependency
    from qdrant_client import AsyncQdrantClient, models as qmodels  # type: ignore
except Exception:  # pragma: no cover - optional
    AsyncQdrantClient = None  # type: ignore
    qmodels = None  # type: ignore


try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from sentence_transformers import SentenceTransformer as ST
else:  # pragma: no cover - fallback for runtime
    ST = object  # type: ignore

_EMBED_MODEL: ST | None = None
_PG_POOL: asyncpg.Pool | None = None
_PG_INIT = False
_PG_LOCK = asyncio.Lock()
_QDRANT_CLIENT: Any | None = None
_QDRANT_INIT = False


def _default_path() -> str:
    return os.getenv("RAEBURN_MEMORY_PATH", "logs/memory.log")


def _db_path() -> str | None:
    return os.getenv("RAEBURN_DB_PATH")


def _db_url() -> str | None:
    return os.getenv("RAEBURN_DB_URL")


def _pg_min_size() -> int:
    return int(os.getenv("RAEBURN_PG_POOL_MIN_SIZE", "1"))


def _pg_max_size() -> int:
    return int(os.getenv("RAEBURN_PG_POOL_MAX_SIZE", "10"))

def _vector_url() -> str | None:
    return os.getenv("RAEBURN_VECTOR_URL")

def _vector_collection() -> str:
    return os.getenv("RAEBURN_VECTOR_COLLECTION", "memories")


async def _get_pg_pool(url: str) -> asyncpg.Pool:
    global _PG_POOL, _PG_INIT
    async with _PG_LOCK:
        if _PG_POOL is None:
            _PG_POOL = await asyncpg.create_pool(
                url,
                min_size=_pg_min_size(),
                max_size=_pg_max_size(),
            )
        if not _PG_INIT:
            async with _PG_POOL.acquire() as conn:
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS memories (id SERIAL PRIMARY KEY, input TEXT, output TEXT, json JSONB)"
                )
            _PG_INIT = True
    assert _PG_POOL is not None
    return _PG_POOL


def _embed(text: str) -> list[float] | None:
    if SentenceTransformer is None:
        return None
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        model_name = os.getenv("RAEBURN_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _EMBED_MODEL = SentenceTransformer(model_name)
    vec = _EMBED_MODEL.encode(text)
    if hasattr(vec, "tolist"):
        return vec.tolist()
    return list(vec)


async def _get_qdrant(url: str):
    global _QDRANT_CLIENT, _QDRANT_INIT
    if AsyncQdrantClient is None:
        raise RuntimeError("qdrant-client not installed")
    if _QDRANT_CLIENT is None:
        _QDRANT_CLIENT = AsyncQdrantClient(url=url)
    if not _QDRANT_INIT:
        collection = _vector_collection()
        try:
            await _QDRANT_CLIENT.get_collection(collection)
        except Exception:
            dim = len(_embed("init") or []) or 1
            await _QDRANT_CLIENT.recreate_collection(
                collection,
                vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
            )
        _QDRANT_INIT = True
    return _QDRANT_CLIENT

class MemoryStore:
    """Persist and search memories using either a log file or database."""

    def __init__(
        self,
        path: str | None = None,
        db_path: str | None = None,
        db_url: str | None = None,
        vector_url: str | None = None,
        vector_collection: str | None = None,
    ):
        self.db_path = db_path or _db_path()
        self.db_url = db_url or _db_url()
        self.path = path or _default_path()
        self.vector_url = vector_url or _vector_url()
        self.vector_collection = vector_collection or _vector_collection()
        self._lock = asyncio.Lock()

    async def _init_db(self) -> None:
        assert self.db_path is not None
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(
                "CREATE TABLE IF NOT EXISTS memories (\n"
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                "  input TEXT,\n"
                "  output TEXT,\n"
                "  json TEXT\n"
                ")"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_io ON memories(input, output)"
            )
            await db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(input, output)"
            )
            await db.execute(
                "CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memories BEGIN\n"
                "  INSERT INTO memory_fts(rowid, input, output) VALUES (new.id, new.input, new.output);\n"
                "END"
            )
            await db.commit()

    async def _init_pg(self) -> None:
        assert self.db_url is not None
        pool = await _get_pg_pool(self.db_url)
        async with pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS memories (id SERIAL PRIMARY KEY, input TEXT, output TEXT, json JSONB)"
            )

    async def save_memory(self, memory: MemoryRecord | dict) -> None:
        record = memory if isinstance(memory, MemoryRecord) else MemoryRecord(**memory)
        if self.db_url:
            async with self._lock:
                await self._init_pg()
                try:
                    pool = await _get_pg_pool(self.db_url)
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO memories (input, output, json) VALUES ($1, $2, $3)",
                            record.input,
                            record.output,
                            json.dumps(record.model_dump(exclude_none=True)),
                        )
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "save", "error": str(exc)})
                    raise
            if self.vector_url:
                try:
                    vec = _embed(record.output or record.input)
                    if vec is not None:
                        client = await _get_qdrant(self.vector_url)
                        await client.upsert(
                            collection_name=self.vector_collection,
                            points=[
                                qmodels.PointStruct(
                                    id=str(uuid4()),
                                    vector=vec,
                                    payload=record.model_dump(exclude_none=True),
                                )
                            ],
                        )
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "vector", "error": str(exc)})
            return
        if self.db_path:
            async with self._lock:
                await self._init_db()
                try:
                    async with aiosqlite.connect(self.db_path) as db:
                        await db.execute("BEGIN")
                        await db.execute(
                            "INSERT INTO memories (input, output, json) VALUES (?, ?, ?)",
                            (
                                record.input,
                                record.output,
                                json.dumps(record.model_dump(exclude_none=True)),
                            ),
                        )
                        await db.commit()
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "save", "error": str(exc)})
                    raise
            if self.vector_url:
                try:
                    vec = _embed(record.output or record.input)
                    if vec is not None:
                        client = await _get_qdrant(self.vector_url)
                        await client.upsert(
                            collection_name=self.vector_collection,
                            points=[
                                qmodels.PointStruct(
                                    id=str(uuid4()),
                                    vector=vec,
                                    payload=record.model_dump(exclude_none=True),
                                )
                            ],
                        )
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "vector", "error": str(exc)})
            return

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            async with aiofiles.open(self.path, 'a') as f:
                await f.write(json.dumps(record.model_dump(exclude_none=True)) + '\n')
        except Exception as exc:  # noqa: BLE001
            await log_event("memory_error", {"action": "save", "error": str(exc)})
            raise
        if self.vector_url:
            try:
                vec = _embed(record.output or record.input)
                if vec is not None:
                    client = await _get_qdrant(self.vector_url)
                    await client.upsert(
                        collection_name=self.vector_collection,
                        points=[
                            qmodels.PointStruct(
                                id=str(uuid4()),
                                vector=vec,
                                payload=record.model_dump(exclude_none=True),
                            )
                        ],
                    )
            except Exception as exc:  # noqa: BLE001
                await log_event("memory_error", {"action": "vector", "error": str(exc)})

    async def search_memories(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        """Return up to ``limit`` memories containing the query."""
        if self.vector_url:
            try:
                vec = _embed(query)
                if vec is not None:
                    client = await _get_qdrant(self.vector_url)
                    hits = await client.search(
                        collection_name=self.vector_collection,
                        query_vector=vec,
                        limit=limit,
                    )
                    return [MemoryRecord.model_validate(h.payload) for h in hits]
            except Exception as exc:  # noqa: BLE001
                await log_event("memory_error", {"action": "vector_search", "error": str(exc)})
        if self.db_url:
            async with self._lock:
                await self._init_pg()
                try:
                    pool = await _get_pg_pool(self.db_url)
                    async with pool.acquire() as conn:
                        rows = await conn.fetch(
                            "SELECT json FROM memories WHERE input ILIKE '%' || $1 || '%' OR output ILIKE '%' || $1 || '%' ORDER BY id DESC LIMIT $2",
                            query,
                            limit,
                        )
                    return [MemoryRecord.model_validate(json.loads(r["json"])) for r in rows]
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "search", "error": str(exc)})
                    raise
        if self.db_path:
            async with self._lock:
                await self._init_db()
                try:
                    async with aiosqlite.connect(self.db_path) as db:
                        await db.execute("BEGIN")
                        async with db.execute(
                            "SELECT m.json FROM memory_fts JOIN memories m ON memory_fts.rowid = m.id WHERE memory_fts MATCH ? ORDER BY m.id DESC LIMIT ?",
                            (query, limit),
                        ) as cursor:
                            rows = await cursor.fetchall()
                        await db.commit()
                    return [MemoryRecord.model_validate(json.loads(r[0])) for r in rows]
                except Exception as exc:  # noqa: BLE001
                    await log_event("memory_error", {"action": "search", "error": str(exc)})
                    raise

        if not os.path.exists(self.path):
            return []

        results = []
        try:
            async with aiofiles.open(self.path) as f:
                lines = await f.readlines()
        except Exception as exc:  # noqa: BLE001
            await log_event("memory_error", {"action": "search", "error": str(exc)})
            raise

        for line in reversed(lines):
            try:
                mem = json.loads(line)
            except json.JSONDecodeError:
                continue

            if query.lower() in mem.get("input", "").lower() or query.lower() in mem.get("output", "").lower():
                results.append(MemoryRecord.model_validate(mem))
                if len(results) >= limit:
                    break

        return results
