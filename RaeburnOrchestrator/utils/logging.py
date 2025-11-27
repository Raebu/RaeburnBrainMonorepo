from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any, MutableMapping

import aiofiles  # type: ignore
import aiofiles.os  # type: ignore
import aiosqlite  # type: ignore
import httpx
import structlog
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

logger = structlog.get_logger()

# Set up optional OpenTelemetry metrics if an exporter URL is provided
OTEL_EVENT_COUNTER = None
OTEL_QUALITY_HIST = None
otel_url = os.getenv("RAEBURN_OTEL_EXPORTER_URL")
if otel_url:
    resource = Resource.create({"service.name": "raeburn-orchestrator"})
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otel_url, timeout=5)
    )
    provider = MeterProvider(metric_readers=[reader], resource=resource)
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(__name__)
    OTEL_EVENT_COUNTER = meter.create_counter("raeburn_log_events")
    OTEL_QUALITY_HIST = meter.create_histogram("raeburn_quality_score")

async def _rotate(path: str, max_bytes: int) -> None:
    if await aiofiles.os.path.exists(path):
        stat = await aiofiles.os.stat(path)
        if stat.st_size > max_bytes:
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            await aiofiles.os.rename(path, f"{path}.{ts}")


async def log_event(event: str, data: dict[str, Any]) -> None:
    """Write an event to the orchestrator log as JSON."""
    record: MutableMapping[str, Any] = {"event": event, **data}
    record = structlog.processors.TimeStamper(key="timestamp", fmt="iso", utc=True)(logger, "info", record)
    json_line = structlog.processors.JSONRenderer()(logger, "info", record)

    if OTEL_EVENT_COUNTER is not None:
        OTEL_EVENT_COUNTER.add(1, {"event": event})

    db_path = os.getenv("RAEBURN_DB_PATH")
    if db_path:
        try:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("CREATE TABLE IF NOT EXISTS logs (json TEXT)")
                await db.execute("INSERT INTO logs (json) VALUES (?)", (json_line,))
                await db.commit()
            return
        except Exception:  # noqa: BLE001
            raise

    log_dir = os.getenv("RAEBURN_LOG_PATH", "logs")
    os.makedirs(log_dir, exist_ok=True)
    max_bytes = int(os.getenv("RAEBURN_LOG_MAX_BYTES", "5000000"))
    path = os.path.join(log_dir, "orchestrator.log")
    await _rotate(path, max_bytes)
    try:
        async with aiofiles.open(path, "a") as f:
            await f.write(str(json_line) + "\n")
    except Exception:
        raise

    stream_url = os.getenv("RAEBURN_LOG_STREAM_URL")
    if stream_url:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(stream_url, json=json.loads(json_line))

