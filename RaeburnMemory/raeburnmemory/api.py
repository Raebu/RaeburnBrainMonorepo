from fastapi import FastAPI, Depends, HTTPException, status, Header
from pydantic import BaseModel
from threading import Lock
import time
import os
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .memory_graph import MemoryGraph


API_KEY = os.getenv("RAEBURN_API_KEY")
RATE_LIMIT = int(os.getenv("RAEBURN_RATE_LIMIT", "0"))
RATE_LIMIT_CALLS: Dict[str, List[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, limit: int) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = 60.0
        self.calls = RATE_LIMIT_CALLS

    async def dispatch(self, request, call_next):
        if self.limit <= 0:
            return await call_next(request)
        client = request.client.host if request.client else "anon"
        now = time.time()
        times = self.calls.setdefault(client, [])
        times[:] = [t for t in times if now - t < self.window]
        if len(times) >= self.limit:
            return Response("Too Many Requests", status_code=429)
        times.append(now)
        return await call_next(request)


app = FastAPI()
if RATE_LIMIT:
    app.add_middleware(RateLimitMiddleware, limit=RATE_LIMIT)

_graph_lock = Lock()


@app.on_event("shutdown")
def _close_graph() -> None:
    graph = getattr(app.state, "graph", None)
    if graph is not None:
        graph.close()
        app.state.graph = None


def get_memory_graph() -> MemoryGraph:
    """Return the application's MemoryGraph, creating it if needed."""
    graph = getattr(app.state, "graph", None)
    if graph is None:
        with _graph_lock:
            graph = getattr(app.state, "graph", None)
            if graph is None:
                graph = MemoryGraph(embedding_model=None)
                app.state.graph = graph
    return graph


async def require_auth(authorization: str | None = Header(None)) -> None:
    if API_KEY is None:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.split()[1]
    if token != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class SimilarRequest(BaseModel):
    text: str | None = None
    top_k: int = 5


@app.get("/memory/graph")
async def get_graph(
    graph: MemoryGraph = Depends(get_memory_graph),
    _: None = Depends(require_auth),
):
    return await graph.export_async(path=False)


@app.post("/memory/similar")
async def post_similar(
    req: SimilarRequest,
    graph: MemoryGraph = Depends(get_memory_graph),
    _: None = Depends(require_auth),
):
    if not req.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="text field required"
        )
    if graph.vector_index.ntotal == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No embeddings available"
        )
    ids = graph.get_similar_prompts(req.text, top_k=req.top_k)
    return {"ids": ids}
