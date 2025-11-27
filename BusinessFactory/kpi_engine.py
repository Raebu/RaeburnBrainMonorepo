"""KPI engine for tracking mission/business metrics."""

from __future__ import annotations

from typing import Dict, Any

from RaeburnBrainAI.memory import MemoryStore

_KPI_TAG = ["kpi"]


def record_kpi(business_id: str, name: str, value: float, meta: Dict[str, Any] | None = None) -> None:
    """Persist a KPI update to the memory store."""
    payload = {"business_id": business_id, "kpi": name, "value": value, **(meta or {})}
    MemoryStore().write(agent_id=business_id, text=str(payload), tags=[*_KPI_TAG, name], importance=0.7)


def snapshot_kpis(business_id: str, limit: int = 100) -> list[Dict[str, Any]]:
    """Return recent KPI entries for a business."""
    entries = MemoryStore().get_relevant(business_id, query="", limit=limit, tags=_KPI_TAG)
    results: list[Dict[str, Any]] = []
    for entry in entries:
        try:
            results.append(eval(entry.text))  # noqa: S307 - trusted internal format
        except Exception:
            results.append({"text": entry.text})
    return results
