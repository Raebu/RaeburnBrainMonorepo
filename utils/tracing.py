from __future__ import annotations

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from contextlib import asynccontextmanager

otel_url = os.getenv("RAEBURN_OTEL_TRACE_URL")
if otel_url:
    resource = Resource.create({"service.name": "raeburn-orchestrator"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otel_url, timeout=5))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)


@asynccontextmanager
async def async_span(name: str, tracer_obj=tracer, **attrs):
    """Async context manager wrapping ``tracer.start_as_current_span``."""
    cm = tracer_obj.start_as_current_span(name, **attrs)
    if hasattr(cm, "__aenter__"):
        async with cm:
            yield
    else:
        with cm:
            yield
