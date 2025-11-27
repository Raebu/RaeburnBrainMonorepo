"""Persistent memory graph implementation.

The graph JSON is written to ``db_path`` which defaults to
``~/.raeburnbrain/graph.json``. Embedding vectors are stored next to the graph
in ``db_path + '.vectors.npy'`` and a mapping of prompt IDs to vector rows is
kept in ``db_path + '.map.json'``.
"""

try:
    import networkx as nx
except ImportError:  # pragma: no cover - optional dependency
    nx = None
import os
import json
from datetime import datetime
from dataclasses import dataclass, asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import asyncio
import sys

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None
import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover - optional dependency
    faiss = None
from filelock import FileLock
import sqlite3

try:
    import pgvector
    from pgvector import utils as pgvector_utils
except ImportError:  # pragma: no cover - optional dependency
    pgvector = None
    pgvector_utils = None

try:
    from qdrant_client import QdrantClient
except ImportError:  # pragma: no cover - optional dependency
    QdrantClient = None


class DummyModel:
    """Fallback model used when no embedding model is available."""

    def encode(self, texts):
        return [np.zeros(384, dtype=np.float32) for _ in texts]


@dataclass
class Prompt:
    id: str
    text: str
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    topic: Optional[str] = None


@dataclass
class Response:
    id: str
    text: str
    model: Optional[str] = None
    agent_id: Optional[str] = None
    score: Optional[float] = None
    timestamp: Optional[str] = None


@dataclass
class Agent:
    id: str
    name: str
    traits: Optional[str] = None


@dataclass
class Session:
    id: str
    start_time: Optional[str] = None


@dataclass
class Edge:
    source: str
    target: str
    relation: str


_QDRANT_POOL: Dict[str, "QdrantClient"] = {}


if nx is None:

    class SimpleDiGraph:
        def __init__(self):
            self.nodes = {}
            self._adj = {}

        def add_node(self, node_id, **attrs):
            self.nodes[node_id] = {"id": node_id, **attrs}
            self._adj.setdefault(node_id, {})

        def add_edge(self, u, v, **attrs):
            self._adj.setdefault(u, {})
            self._adj[u][v] = attrs

        def successors(self, node_id):
            return list(self._adj.get(node_id, {}).keys())

        @property
        def edges(self):
            return {
                (u, v): attrs
                for u, nbrs in self._adj.items()
                for v, attrs in nbrs.items()
            }

    class _JSONGraph:
        @staticmethod
        def node_link_data(graph):
            links = [
                {"source": u, "target": v, **attrs}
                for u, nbrs in getattr(graph, "_adj", {}).items()
                for v, attrs in nbrs.items()
            ]
            return {"nodes": list(graph.nodes.values()), "links": links}

        @staticmethod
        def node_link_graph(data):
            g = SimpleDiGraph()
            for n in data.get("nodes", []):
                nid = n.pop("id")
                g.add_node(nid, **n)
            for e in data.get("links", []):
                src = e.pop("source")
                tgt = e.pop("target")
                g.add_edge(src, tgt, **e)
            return g

    nx = type(
        "nx",
        (),
        {
            "DiGraph": SimpleDiGraph,
            "readwrite": type("rw", (), {"json_graph": _JSONGraph}),
        },
    )


if faiss is None:

    class SimpleIndex:
        def __init__(self, dim):
            self.vectors = []
            self.dim = dim

        @property
        def ntotal(self) -> int:
            return len(self.vectors)

        def add(self, arr: np.ndarray) -> None:
            for v in arr:
                self.vectors.append(np.array(v))

        def reconstruct(self, i: int) -> np.ndarray:
            return self.vectors[i]

        def search(self, arr: np.ndarray, k: int):
            q = arr[0]
            dists = [float(np.sum((v - q) ** 2)) for v in self.vectors]
            idx = np.argsort(dists)[:k]
            return np.array([dists[i] for i in idx]).reshape(1, -1), np.array(
                idx
            ).reshape(1, -1)

    def write_index(index: "SimpleIndex", path: str) -> None:  # type: ignore
        data = (
            np.vstack(index.vectors)
            if index.vectors
            else np.empty((0, index.dim), dtype=np.float32)
        )
        with open(path, "wb") as f:
            np.save(f, data)

    def read_index(path: str) -> "SimpleIndex":  # type: ignore
        with open(path, "rb") as f:
            arr = np.load(f)
        idx = SimpleIndex(arr.shape[1] if arr.size else 0)
        if arr.size:
            idx.add(arr)
        return idx

    faiss = type(
        "faiss",
        (),
        {
            "IndexFlatL2": SimpleIndex,
            "write_index": write_index,
            "read_index": read_index,
            "__version__": "1.12.0",
        },
    )
    # make fallback importable as "faiss" for modules that expect it
    sys.modules.setdefault("faiss", faiss)


class MemoryGraph:
    def __init__(
        self,
        db_path: str = "~/.raeburnbrain/graph.json",
        embedding_model: Optional[str] = "all-MiniLM-L6-v2",
        storage_backend: str = "json",
        vector_backend: str = "faiss",
        qdrant_url: str = ":memory:",
    ) -> None:
        """Create a new MemoryGraph.

        Parameters
        ----------
        db_path : str, optional
            Location of the graph JSON file. Associated vector and map files are
            created by appending ``.vectors.npy`` and ``.map.json`` to this
            path.
        embedding_model : str or None, optional
            Name of a SentenceTransformer model to load. Set to ``None`` to use
            the lightweight dummy encoder.
        storage_backend : {"json", "sqlite"}, optional
            Select persistence method. ``"json"`` stores data in JSON files
            while ``"sqlite"`` uses a SQLite database with pgvector embeddings.
        vector_backend : {"faiss", "qdrant"}, optional
            Vector storage implementation. ``"faiss"`` uses an in-memory FAISS
            index while ``"qdrant"`` stores vectors in a Qdrant collection.
        qdrant_url : str, optional
            Qdrant endpoint or ``":memory:"`` for the embedded server.
        """

        self.graph = nx.DiGraph()
        self.storage_backend = storage_backend
        self.db_path = os.path.expanduser(db_path)
        if self.storage_backend == "sqlite" and self.db_path.endswith(".json"):
            self.db_path = self.db_path[:-5] + ".db"
        env_model = os.getenv("RAEBURN_EMBED_MODEL")
        if env_model is not None:
            embedding_model = None if env_model.lower() == "none" else env_model

        if embedding_model is None or SentenceTransformer is None:
            self.model = DummyModel()
        else:
            self.model = SentenceTransformer(embedding_model)
        self.vector_backend = vector_backend
        self.qdrant_url = qdrant_url
        self._qdrant_map = {}
        self.vector_index = self._init_vector_index()
        self.vector_map = {}
        if self.storage_backend == "json":
            self._vectors_path = self.db_path + ".vectors.npy"
            self._index_path = self.db_path + ".faiss"
            self._map_path = self.db_path + ".map.json"
            self._lock = FileLock(self.db_path + ".lock")
        else:
            self._conn = None
            self._lock = None
        self.load()

    def _init_vector_index(self):
        dim = 384  # for MiniLM
        if self.vector_backend == "qdrant" and QdrantClient is not None:
            client = _QDRANT_POOL.get(self.qdrant_url)
            if client is None:
                client = QdrantClient(self.qdrant_url, prefer_grpc=True)
                _QDRANT_POOL[self.qdrant_url] = client
            self._qdrant_collection = "memory_vectors"
            if not client.collection_exists(self._qdrant_collection):
                from qdrant_client.http import models

                client.recreate_collection(
                    collection_name=self._qdrant_collection,
                    vectors_config=models.VectorParams(
                        size=dim, distance=models.Distance.COSINE
                    ),
                )
            return client
        return faiss.IndexFlatL2(dim)

    # -- SQLite helpers -------------------------------------------------
    def _init_db(self) -> None:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, type TEXT, data TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS edges (src TEXT, dst TEXT, relation TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, vector BLOB)"
        )
        self._conn.commit()

    def _load_from_db(self) -> None:
        self._init_db()
        cur = self._conn.cursor()
        for node_id, typ, data_json in cur.execute("SELECT id, type, data FROM nodes"):
            attrs = json.loads(data_json or "{}")
            self.graph.add_node(node_id, type=typ, **attrs)
        for src, dst, rel in cur.execute("SELECT src, dst, relation FROM edges"):
            self.graph.add_edge(src, dst, relation=rel)
        self.vector_index = self._init_vector_index()
        self.vector_map = {}
        for node_id, vec_blob in cur.execute("SELECT id, vector FROM vectors"):
            if pgvector_utils is not None:
                vec = pgvector_utils.from_db_binary(vec_blob)
            else:
                vec = np.frombuffer(vec_blob, dtype=np.float32)
            self.vector_index.add(np.array([vec]))
            self.vector_map[node_id] = self.vector_index.ntotal - 1

    def _migrate_json_to_db(self, json_path: str) -> None:
        """Load JSON graph files and store them into a SQLite database."""
        self._init_db()
        with open(json_path, "r") as f:
            data = json.load(f)
        graph = nx.readwrite.json_graph.node_link_graph(data)
        for nid, attrs in graph.nodes.items():
            typ = attrs.get("type")
            self._save_node(nid, typ, {k: v for k, v in attrs.items() if k != "type"})
        for (u, v), attrs in getattr(graph, "edges", {}).items():
            self._save_edge(u, v, attrs.get("relation"))
        self._conn.commit()
        map_path = json_path + ".map.json"
        vec_path = json_path + ".vectors.npy"
        faiss_path = json_path + ".faiss"
        if os.path.exists(map_path):
            with open(map_path, "r") as f:
                mapping = {k: int(v) for k, v in json.load(f).items()}
            if os.path.exists(faiss_path) and hasattr(faiss, "read_index"):
                index = faiss.read_index(faiss_path)
                for nid, idx in mapping.items():
                    self._save_vector(nid, index.reconstruct(idx))
            elif os.path.exists(vec_path):
                vectors = np.load(vec_path)
                for nid, idx in mapping.items():
                    if idx < len(vectors):
                        self._save_vector(nid, vectors[idx].astype(np.float32))

    def _save_node(
        self, node_id: str, node_type: Optional[str], data: Dict[str, Any]
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO nodes (id, type, data) VALUES (?, ?, ?)",
            (node_id, node_type, json.dumps(data)),
        )
        self._conn.commit()

    def _save_edge(self, u: str, v: str, relation: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO edges (src, dst, relation) VALUES (?, ?, ?)", (u, v, relation)
        )
        self._conn.commit()

    def _save_vector(self, node_id: str, vec: np.ndarray) -> None:
        cur = self._conn.cursor()
        if pgvector_utils is not None:
            blob = pgvector_utils.to_db_binary(vec)
        else:
            blob = vec.tobytes()
        cur.execute(
            "INSERT OR REPLACE INTO vectors (id, vector) VALUES (?, ?)",
            (node_id, blob),
        )
        self._conn.commit()

    def _persist_vectors(self) -> None:
        if self.storage_backend != "json" or self.vector_backend != "faiss":
            return
        if self.vector_index.ntotal == 0:
            return
        with self._lock:
            if hasattr(faiss, "write_index"):
                faiss.write_index(self.vector_index, self._index_path)
                with open(self._map_path, "w") as f:
                    json.dump(self.vector_map, f)
            else:
                vectors = np.vstack(
                    [
                        self.vector_index.reconstruct(i)
                        for i in range(self.vector_index.ntotal)
                    ]
                )
                np.save(self._vectors_path, vectors)
                with open(self._map_path, "w") as f:
                    json.dump(self.vector_map, f)

    def add_interaction(
        self,
        prompt: Union[Prompt, Dict[str, Any]],
        response: Union[Response, Dict[str, Any]],
        agent: Union[Agent, Dict[str, Any]],
        session_id: str,
    ) -> None:
        timestamp = datetime.utcnow().isoformat()

        # Add nodes
        if is_dataclass(prompt):
            prompt = asdict(prompt)
        if is_dataclass(response):
            response = asdict(response)
        if is_dataclass(agent):
            agent = asdict(agent)
        prompt.pop("timestamp", None)
        response.pop("timestamp", None)
        self.graph.add_node(prompt["id"], type="prompt", **prompt, timestamp=timestamp)
        self.graph.add_node(
            response["id"], type="response", **response, timestamp=timestamp
        )
        self.graph.add_node(agent["id"], type="agent", **agent)
        self.graph.add_node(session_id, type="session", start_time=timestamp)

        # Add edges
        self.graph.add_edge(prompt["id"], response["id"], relation="responded_with")
        self.graph.add_edge(response["id"], agent["id"], relation="generated_by")
        self.graph.add_edge(prompt["id"], session_id, relation="belongs_to")

        # Store vector
        emb = self.model.encode([prompt["text"]])[0].astype(np.float32)
        if self.vector_backend == "qdrant" and QdrantClient is not None:
            from qdrant_client.http import models
            import uuid

            qid = str(uuid.uuid5(uuid.NAMESPACE_URL, prompt["id"]))
            self.vector_index.upsert(
                collection_name=self._qdrant_collection,
                points=[models.PointStruct(id=qid, vector=emb.tolist())],
            )
            self._qdrant_map[qid] = prompt["id"]
        else:
            self.vector_index.add(np.array([emb]))
            self.vector_map[prompt["id"]] = self.vector_index.ntotal - 1
        if self.storage_backend == "json":
            self._persist_vectors()
        else:
            self._save_node(prompt["id"], "prompt", {**prompt, "timestamp": timestamp})
            self._save_node(
                response["id"], "response", {**response, "timestamp": timestamp}
            )
            self._save_node(agent["id"], "agent", agent)
            self._save_node(session_id, "session", {"start_time": timestamp})
            self._save_edge(prompt["id"], response["id"], "responded_with")
            self._save_edge(response["id"], agent["id"], "generated_by")
            self._save_edge(prompt["id"], session_id, "belongs_to")
            self._save_vector(prompt["id"], emb)

    def get_similar_prompts(self, text: str, top_k: int = 5) -> List[str]:
        emb = self.model.encode([text])[0].astype(np.float32)
        if self.vector_backend == "qdrant" and QdrantClient is not None:
            hits = self.vector_index.search(
                collection_name=self._qdrant_collection,
                query_vector=emb.tolist(),
                limit=top_k,
            )
            results = []
            for h in hits:
                hid = h.get("id") if isinstance(h, dict) else getattr(h, "id", None)
                if hid is not None:
                    results.append(self._qdrant_map.get(str(hid), str(hid)))
            return results
        _distances, indices = self.vector_index.search(np.array([emb]), top_k)

        matches = []
        for idx in indices[0]:
            for node_id, ix in self.vector_map.items():
                if ix == idx:
                    matches.append(node_id)
                    break
        return matches

    def export(self, path: Optional[Union[str, bool]] = None) -> Dict[str, Any]:
        """Export the graph data and optionally write it to ``path``."""
        data = nx.readwrite.json_graph.node_link_data(self.graph)
        if path is not False:
            if not path:
                path = (
                    self.db_path
                    if self.storage_backend == "json"
                    else self.db_path + ".json"
                )
            if self.storage_backend == "json":
                with self._lock:
                    with open(path, "w") as f:
                        json.dump(data, f, indent=2)
                    self._persist_vectors()
            else:
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
        return data

    def load(self) -> None:
        if self.storage_backend == "json":
            with self._lock:
                if os.path.exists(self.db_path):
                    try:
                        with open(self.db_path, "r") as f:
                            data = json.load(f)
                        self.graph = nx.readwrite.json_graph.node_link_graph(data)
                    except Exception:  # pragma: no cover - corrupted file
                        self.graph = nx.DiGraph()
                if os.path.exists(self._map_path):
                    try:
                        with open(self._map_path, "r") as f:
                            self.vector_map = {
                                k: int(v) for k, v in json.load(f).items()
                            }
                    except Exception:  # pragma: no cover - corrupted file
                        self.vector_map = {}
                if hasattr(faiss, "read_index") and os.path.exists(self._index_path):
                    try:
                        self.vector_index = faiss.read_index(self._index_path)
                    except Exception:  # pragma: no cover - corrupted file
                        self.vector_index = self._init_vector_index()
                elif os.path.exists(self._vectors_path):
                    try:
                        vectors = np.load(self._vectors_path)
                        if vectors.size:
                            self.vector_index.add(vectors.astype(np.float32))
                    except Exception:  # pragma: no cover - corrupted file
                        pass
        else:
            json_path = self.db_path[:-3] + ".json"
            if not os.path.exists(self.db_path) and os.path.exists(json_path):
                self._migrate_json_to_db(json_path)
            try:
                self._load_from_db()
            except sqlite3.DatabaseError:  # pragma: no cover - corrupted db
                self.graph = nx.DiGraph()
                self.vector_index = self._init_vector_index()
                self.vector_map = {}

    def visualise_prompt_chain(
        self, prompt_id: str, depth: int = 3
    ) -> List[Tuple[str, str]]:
        chain = []
        current = prompt_id
        for _ in range(depth):
            successors = list(self.graph.successors(current))
            if not successors:
                break
            next_id = successors[0]
            chain.append((current, next_id))
            current = next_id
        return chain

    def link_similar_prompts(self, threshold: float = 0.85) -> None:
        ids = list(self.vector_map.keys())
        vectors = [self.vector_index.reconstruct(self.vector_map[i]) for i in ids]
        for i, vec1 in enumerate(vectors):
            for j, vec2 in enumerate(vectors):
                if i != j:
                    sim = np.dot(vec1, vec2) / (
                        np.linalg.norm(vec1) * np.linalg.norm(vec2)
                    )
                    if sim > threshold:
                        self.graph.add_edge(
                            ids[i], ids[j], relation="semantically_similar"
                        )

    # -- lifecycle ------------------------------------------------------

    def close(self) -> None:
        """Close any open database connection."""
        if hasattr(self, "_conn") and self._conn is not None:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "MemoryGraph":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - cleanup during GC
        try:
            self.close()
        except Exception:
            pass

    # -- async helpers --------------------------------------------------

    async def add_interaction_async(
        self,
        prompt: Union[Prompt, Dict[str, Any]],
        response: Union[Response, Dict[str, Any]],
        agent: Union[Agent, Dict[str, Any]],
        session_id: str,
    ) -> None:
        await asyncio.to_thread(
            self.add_interaction, prompt, response, agent, session_id
        )

    async def batch_add(
        self,
        interactions: Iterable[
            Tuple[
                Prompt | Dict[str, Any],
                Response | Dict[str, Any],
                Agent | Dict[str, Any],
                str,
            ]
        ],
    ) -> None:
        await asyncio.gather(
            *[self.add_interaction_async(p, r, a, s) for p, r, a, s in interactions]
        )

    async def export_async(
        self, path: Optional[Union[str, bool]] = None
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.export, path)
