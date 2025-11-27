"""SQLite-backed memory store with sharding, TTL, tags, and FTS search."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

DEFAULT_MEMORY_DIR = Path(os.getenv("RAEBURN_MEMORY_DIR", "runtime/cache/memory_shards"))


@dataclass
class MemoryEntry:
    text: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None


class MemoryStore:
    """Per-agent sharded memory store using SQLite+FTS5."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else DEFAULT_MEMORY_DIR
        self._lock = threading.Lock()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _db_path(self, agent_id: str | None) -> Path:
        shard = agent_id or "global"
        return self.base_dir / f"{shard}_shard.db"

    def _connect(self, agent_id: str | None) -> sqlite3.Connection:
        path = self._db_path(agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "agent TEXT,"
            "text TEXT,"
            "tags TEXT,"
            "importance REAL,"
            "created_at REAL,"
            "expires_at REAL"
            ")"
        )
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(text, content='entries', content_rowid='id')"
        )
        conn.execute(
            "CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries "
            "BEGIN "
            "  INSERT INTO memory_fts(rowid, text) VALUES (new.id, new.text); "
            "END;"
        )
        conn.commit()

    def _prune_expired(self, conn: sqlite3.Connection) -> None:
        now = time.time()
        conn.execute("DELETE FROM entries WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
        conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        tags: list[str] = []
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except Exception:
            tags = []
        return MemoryEntry(
            text=row["text"],
            tags=tags,
            importance=row["importance"] or 0.0,
            created_at=row["created_at"] or time.time(),
            expires_at=row["expires_at"],
        )

    def write(
        self,
        agent_id: str,
        text: str,
        *,
        tags: Sequence[str] | None = None,
        importance: float = 0.5,
        ttl: float | None = None,
    ) -> None:
        expires_at = time.time() + ttl if ttl else None
        payload_tags = json.dumps(list(tags or []))
        with self._lock:
            conn = self._connect(agent_id)
            self._prune_expired(conn)
            conn.execute(
                "INSERT INTO entries (agent, text, tags, importance, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (agent_id, text, payload_tags, importance, time.time(), expires_at),
            )
            conn.commit()
            conn.close()

    def get(self, agent_id: str, limit: int = 5) -> List[MemoryEntry]:
        with self._lock:
            conn = self._connect(agent_id)
            self._prune_expired(conn)
            cur = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = cur.fetchall()
            conn.close()
        return [self._row_to_entry(r) for r in rows]

    def search(self, agent_id: str, query: str, limit: int = 5) -> List[MemoryEntry]:
        with self._lock:
            conn = self._connect(agent_id)
            self._prune_expired(conn)
            cur = conn.execute(
                "SELECT e.* FROM memory_fts f JOIN entries e ON e.id = f.rowid "
                "WHERE memory_fts MATCH ? ORDER BY e.created_at DESC LIMIT ?",
                (query, limit),
            )
            rows = cur.fetchall()
            conn.close()
        return [self._row_to_entry(r) for r in rows]

    def by_tag(self, agent_id: str, tag: str, limit: int = 5) -> List[MemoryEntry]:
        with self._lock:
            conn = self._connect(agent_id)
            self._prune_expired(conn)
            cur = conn.execute(
                "SELECT * FROM entries WHERE tags LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{tag}%", limit),
            )
            rows = cur.fetchall()
            conn.close()
        return [self._row_to_entry(r) for r in rows]

    def get_relevant(
        self,
        agent_id: str,
        query: str,
        limit: int = 5,
        tags: Sequence[str] | None = None,
    ) -> List[MemoryEntry]:
        combined: list[MemoryEntry] = []
        if tags:
            for tag in tags:
                combined.extend(self.by_tag(agent_id, tag, limit=limit))
        if query:
            combined.extend(self.search(agent_id, query, limit=limit))
        else:
            combined.extend(self.get(agent_id, limit=limit))
        combined.sort(key=lambda m: m.created_at, reverse=True)
        seen: set[tuple[str, tuple[str, ...]]] = set()
        deduped: list[MemoryEntry] = []
        for m in combined:
            key = (m.text, tuple(m.tags))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(m)
        return deduped[:limit]

    def prune(self, agent_id: str) -> None:
        with self._lock:
            conn = self._connect(agent_id)
            self._prune_expired(conn)
            conn.close()

    def wipe(self, agent_id: str) -> None:
        """Delete a shard file for a clean slate."""
        path = self._db_path(agent_id)
        if path.exists():
            path.unlink()

    def snapshot(self, agent_id: str, dest: Path | str) -> Path:
        """Export shard entries to a JSON file."""
        dest_path = Path(dest)
        entries = [e.__dict__ for e in self.get(agent_id, limit=10000)]
        dest_path.write_text(json.dumps(entries, indent=2))
        return dest_path
