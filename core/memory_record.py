from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MemoryRecord(BaseModel):
    """Persisted memory item stored by the orchestrator."""

    input: str
    output: str | None = None
    agent: str | None = None
    timestamp: str | None = None
    score: float | None = None
    session: str | None = None
    mode: str | None = None
    model_used: str | None = None
    duration_ms: int | None = None
    priority: int | None = None

    model_config = ConfigDict(extra="ignore")
