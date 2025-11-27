from .memory_graph import (
    MemoryGraph,
    faiss,
    Prompt,
    Response,
    Agent,
    Session,
)

try:  # optional FastAPI dependency
    from .api import app, get_memory_graph
    from . import cli

    __all__ = [
        "MemoryGraph",
        "faiss",
        "Prompt",
        "Response",
        "Agent",
        "Session",
        "app",
        "get_memory_graph",
        "cli",
    ]
except Exception:  # pragma: no cover - FastAPI may be missing
    from . import cli

    __all__ = [
        "MemoryGraph",
        "faiss",
        "Prompt",
        "Response",
        "Agent",
        "Session",
        "cli",
    ]
