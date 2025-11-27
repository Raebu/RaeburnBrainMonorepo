from __future__ import annotations

"""HTTP server exposing observability and agent lifecycle endpoints."""

import json
import logging
import os
import time
from dataclasses import asdict

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import (
    Counter,
    Gauge,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    generate_latest,
)

from .agent import AgentRegistry
from .db import run_migrations
from .core import MemoryStore


class JSONFormatter(logging.Formatter):
    """Format logs as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - log format
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


class MemoryLogHandler(logging.Handler):
    """Send log records to a ``MemoryStore`` for ingestion."""

    def __init__(self, store: MemoryStore, agent_id: str) -> None:
        super().__init__()
        self.store = store
        self.agent_id = agent_id

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple
        msg = self.format(record)
        try:
            self.store.add(self.agent_id, msg, tags=["log"], importance=0.1)
        except Exception:
            pass


def configure_logging(level: int = logging.INFO) -> MemoryStore | None:
    """Configure root logger to output JSON formatted logs.

    If ``RAEBURN_LOG_AGENT`` is set, logs are ingested into a ``MemoryStore`` for
    later retrieval.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)

    store: MemoryStore | None = None
    agent_id = os.getenv("RAEBURN_LOG_AGENT")
    if agent_id:
        store = MemoryStore()
        mem_handler = MemoryLogHandler(store, agent_id)
        mem_handler.setFormatter(JSONFormatter())
        logging.getLogger().addHandler(mem_handler)

    # Set up OpenTelemetry tracing with a simple console exporter
    provider = TracerProvider(resource=Resource.create({"service.name": "raeburn-brain"}))
    trace.set_tracer_provider(provider)
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)

    return store


# Metrics shared across requests
REQUEST_COUNT = Counter("app_requests_total", "Total HTTP requests")
START_TIME = time.time()
UPTIME_GAUGE = Gauge("app_uptime_seconds", "Application uptime in seconds")
REGISTRY = CollectorRegistry()
REGISTRY.register(REQUEST_COUNT)
REGISTRY.register(UPTIME_GAUGE)


def create_app(store: MemoryStore | None = None) -> FastAPI:
    """Create and return the FastAPI application."""
    run_migrations()
    token = os.getenv("RAEBURN_DASHBOARD_TOKEN")
    user = os.getenv("RAEBURN_OAUTH_USER")
    password = os.getenv("RAEBURN_OAUTH_PASS")
    if not token or not user or not password:
        raise SystemExit("RAEBURN_DASHBOARD_TOKEN, RAEBURN_OAUTH_USER and RAEBURN_OAUTH_PASS are required")

    app = FastAPI()
    if store:
        app.state.log_store = store
    FastAPIInstrumentor.instrument_app(app)
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
    registry = AgentRegistry()

    def check_token(token_value: str = Depends(oauth2_scheme)) -> None:
        if token_value != token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"})

    @app.post("/token")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
        if form_data.username != user or form_data.password != password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"access_token": token, "token_type": "bearer"}

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request, credentials: None = Depends(check_token)):
        agents = [asdict(a) for a in registry.list()]
        return templates.TemplateResponse("dashboard.html", {"request": request, "agents": agents})


    @app.middleware("http")
    async def record_metrics(request, call_next):
        REQUEST_COUNT.inc()
        response = await call_next(request)
        return response

    @app.get("/healthz")
    async def healthz(credentials: None = Depends(check_token)) -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/uptime")
    async def uptime(credentials: None = Depends(check_token)) -> dict[str, int]:
        secs = int(time.time() - START_TIME)
        UPTIME_GAUGE.set(secs)
        return {"uptime_seconds": secs}

    @app.get("/metrics")
    async def metrics(credentials: None = Depends(check_token)) -> Response:
        UPTIME_GAUGE.set(int(time.time() - START_TIME))
        data = generate_latest(REGISTRY)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    @app.get("/agents")
    async def list_agents(credentials: None = Depends(check_token)) -> list[dict]:
        return [asdict(a) for a in registry.list()]

    @app.post("/agents")
    async def create_agent(payload: dict, credentials: None = Depends(check_token)) -> dict:
        aid = payload["id"]
        traits = payload.get("traits", [])
        agent = registry.ensure(aid, traits)
        return asdict(agent)

    @app.post("/agents/{agent_id}/mentor")
    async def mentor_agent(agent_id: str, payload: dict, credentials: None = Depends(check_token)) -> dict:
        registry.mentor(agent_id, payload["mentor_id"])
        return {"status": "ok"}

    @app.post("/agents/{agent_id}/clone")
    async def clone_agent(agent_id: str, payload: dict, credentials: None = Depends(check_token)) -> dict:
        new_agent = registry.clone(agent_id, payload["new_id"])
        return asdict(new_agent)

    if store:
        @app.get("/logs")
        async def get_logs(credentials: None = Depends(check_token)) -> list[dict]:
            return [asdict(e) for e in store.get(os.getenv("RAEBURN_LOG_AGENT"), limit=50)]

    return app


__all__ = ["create_app", "configure_logging", "MemoryLogHandler"]
