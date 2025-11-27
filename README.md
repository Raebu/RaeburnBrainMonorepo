# Raeburn Brain AI: Full System Architecture

## Overview

Raeburn Brain AI is a modular, multi-agent, hybrid AI infrastructure for orchestrating local and remote LLMs, memory augmented routing, agent evolution, autonomous decision making, and fully autonomous AI business deployment. It supports plugin discovery, agent lifecycle tracking, performance scoring, contextual memory injection, and scalable team communication.

The core engine includes a lightweight memory store, an asynchronous context injector, and a routing engine powered by pluggable bandit strategies with telemetry.

## Key Subsystems

1. **Core Engine**
   - Memory store with agent sharding and semantic tagging
   - Async context injector returning typed ``Context`` objects
   - Hybrid routing engine with scoring, retry/fallback and telemetry
   - Bandit algorithms (UCB1, Thompson, Softmax) as pluggable strategies
   - Pydantic-based config management
   - Prometheus metrics for memory and routing performance

2. **Model Infrastructure**
   - Pluggable model fetcher (HuggingFace, mirrors)
   - Health checker with synthetic probes
   - Router-wide scoring based on cost, latency, accuracy
   - Local and remote (OpenRouter, Ollama) support
   - Signature verification for model security
   - In-memory caching with `CachedModelFetcher`

3. **Agent Identity & Lifecycle**
   - Trait-based persona generator
   - Title assignment and promotion based on scored performance
   - Sandboxing and demotion for underperformers
   - Agent mentorship, combination, and cloning
   - Persisted in a database table via SQLAlchemy and Alembic

4. **Prompt Management**
   - Dynamic template selection from `agent_templates/`
   - Context injection via Jinja2 engine
   - Chat memory history threading with `chat_templates.json`
   - Mood, tone, and personality modifiers

5. **Memory & Knowledge Layer**
   - TinyDB/SQLite/Postgres adapters with FTS5 or tsvector
   - Auto-pruning of expired or low-importance entries
   - Semantic key/tag indexing and search
   - Log-derived memory entry creation (RAG/fusion planned)

6. **Autonomous Meta-Agent Logic**
   ❌ Not Started
   ❌ Needs Updating
   No code for daily missions, retention scoring, or mentorship loops.

7. **Judging & Voting System**
   - Three-model response competition per prompt
   - Judge LLM (local or remote) selects the best output
   - Winning model is reinforced (score, CPU priority, title)
   - Underperformers tracked and optionally sandboxed
   - Use `Judge` to run competitions and update the `AgentRegistry`

```python
from raeburn_brain.judging import Judge
from raeburn_brain.model import LocalModelFetcher
from raeburn_brain.agent import AgentRegistry

registry = AgentRegistry()
judge = Judge(LocalModelFetcher("judge"), registry)
agents = {
    "a1": LocalModelFetcher("m1"),
    "a2": LocalModelFetcher("m2"),
}
winner = judge.compete("hello", agents).winner_id
print("winner is", winner)
```

8. **Business Factory Mode**
   - Auto-creates new AI-led businesses daily
   - Assigns internal teams to marketing, dev, voice outreach
   - Business types chosen from success patterns or niche detection
   - Loop uses past financial performance to evolve agent specializations
   
   ```python
   from raeburn_brain.business import BusinessFactory
   from raeburn_brain.agent import AgentRegistry
   from raeburn_brain.core import MemoryStore

   factory = BusinessFactory(AgentRegistry(), MemoryStore())
   factory.create_business("biz1", ["marketing", "dev"])
   for _ in range(5):
       factory.record_kpi("biz1", "marketing", 1.0)
   ```

9. **Operational Dashboard & Logs**
   - `/metrics`, `/uptime`, `/healthz` endpoints
   - JSON structured logs ingested into memory via `MemoryLogHandler`
   - Prometheus metrics with Grafana dashboard
   - Optional TLS using `RAEBURN_TLS_CERTFILE`/`RAEBURN_TLS_KEYFILE`

10. **Security & Deployment**
    - Systemd service, Docker Compose, Makefile
    - Secure config validation with Pydantic
    - Signature-enforced model fetching
    - Authenticated dashboards secured with OAuth2 bearer tokens and TLS using
      ``RAEBURN_OAUTH_USER`` and ``RAEBURN_OAUTH_PASS`` for login

11. **Plugin System**
    - Modular folders for new tools or agents
    - Autodiscovery via naming convention (`raeburn_*.py`)
    - `meta.json` provides sandbox, priority, description
    - Dynamic loading on startup or live hot-reload

Plugins are loaded via `PluginManager`, which scans a `plugins/` directory
for Python modules named `raeburn_*.py`. Each plugin can include an optional
`meta.json` next to the module providing metadata like sandboxing and priority.
At package import time the manager discovers all plugins and invokes a
``register(manager)`` function if present. Plugins marked ``{"sandbox": true}``
are loaded but the registration step is skipped to keep them isolated. The
manager also exposes ``reload()`` and ``watch()`` helpers for hot-reloading
during development.

12. **Communications Layer**
    - Async adapters for Telegram, Slack, and Discord using `httpx`
    - Voice pipeline powered by Whisper for STT and gTTS for streaming TTS
    - Local UI terminal with optional Electron wrappers
    - Broadcast mode to Slack/Discord for agent updates

13. **Extensibility Hooks**
    - Judge model configurable (GPT-4, Claude, Qwen, etc.)
    - Additional model health sources (Censys, inference metrics)
    - GPU/CPU routing logic aware of model priority and resource cost
    - GPT-based prompt rewriters and augmenters

## Kubernetes Deployment & GitOps

The `k8s/` directory contains example manifests for running Raeburn Brain AI on a
Kubernetes cluster. A Helm chart under `helm/raeburn-brain` packages these
resources for easy installation. Argo CD watches the repository and keeps the
cluster state in sync with Git. Metrics are scraped by Prometheus using the
provided `ServiceMonitor`, and Alertmanager sends notifications to Slack.
You can also create Kustomize overlays in `k8s/overlays/` for environment-
specific configuration.

Grafana dashboards pull Prometheus metrics using the ConfigMap in
`k8s/base/grafana-dashboard.yaml`. The deployment includes liveness and
readiness probes hitting `/healthz`.

See [docs/gitops.md](docs/gitops.md) for the full deployment workflow.

## Observability Endpoints

Set ``RAEBURN_DASHBOARD_TOKEN`` along with ``RAEBURN_OAUTH_USER`` and
``RAEBURN_OAUTH_PASS`` to enable the protected dashboard.

`create_app()` from ``raeburn_brain.server`` exposes several HTTP endpoints.
Authentication uses the OAuth2 password flow to obtain a bearer token via ``/token``.
Endpoints require this token in the ``Authorization`` header:

- **/token** – exchange username and password for an access token
- **/dashboard** – HTML dashboard showing agent metrics
- **/healthz** – returns `{ "status": "ok" }` to indicate the service is running
- **/uptime** – JSON with the number of seconds the process has been alive
- **/metrics** – Prometheus-formatted metrics including request counters and uptime

If ``RAEBURN_TLS_CERTFILE`` and ``RAEBURN_TLS_KEYFILE`` are set the server can be
started with TLS using uvicorn's ``--ssl-certfile`` and ``--ssl-keyfile``
arguments. When ``RAEBURN_LOG_AGENT`` is defined, ``configure_logging()`` stores
JSON-formatted logs in a ``MemoryStore`` which can be retrieved through the new
``/logs`` endpoint.

Logs emitted through ``configure_logging()`` are JSON formatted for easy parsing
and can be ingested as memory entries when ``RAEBURN_LOG_AGENT`` is enabled.
Traces are produced via OpenTelemetry and exported using the default OTLP
settings.

## Summary

Raeburn Brain AI is an advanced autonomous AI command system. It unifies hybrid model inference, agent memory, prompt selection, scoring, feedback loops, and performance evolution. It is modular, extensible, and built to manage AI-driven businesses, services, and communication agents at scale.

Future work includes integrating structured logging, judge LLM routing, business factory stabilization, sandboxing enforcement, agent lifecycle tracking, and long-term memory analytics.


## Model Infrastructure

The `raeburn_brain.model` module defines pluggable fetchers for local files or real LLM APIs. `LocalModelFetcher` verifies downloaded weights with an HMAC signature. `OpenAIHTTPFetcher`, `HuggingFaceFetcher`, and `ClaudeModelFetcher` call provider endpoints via `httpx` and record real latency and token usage so Prometheus histograms capture cost per request. A `CachedModelFetcher` wrapper can cache responses in memory to avoid duplicate calls. Each fetcher implements a `probe()` method, and a `ModelMetricsStore` persists metrics to SQLite. `FetcherStats` combine latency, accuracy, and cost into a score used by `ModelRegistry` to pick the best model at runtime.

```python
from raeburn_brain.model import (
    LocalModelFetcher,
    OpenAIHTTPFetcher,
    HuggingFaceFetcher,
    ModelRegistry,
    ModelMetricsStore,
)

metrics = ModelMetricsStore()
local = LocalModelFetcher("local-model.bin", signature="abc", secret="key")
remote = OpenAIHTTPFetcher("gpt-3.5-turbo", api_key="sk-...", cost=0.01)
hf = HuggingFaceFetcher("mistralai/Mistral-7B-Instruct-v0.2", api_key="hf_...", cost=0.005)
registry = ModelRegistry([local, remote, hf], metrics=metrics)
response = registry.generate("Hello")
```

## Prompt Management

Prompts are rendered using a Jinja2 environment. ``PromptManager`` loads
templates from a directory (``*.j2`` is the recommended extension) and injects
recent chat history and memory context for the selected agent. Mood and tone
modifiers are exposed as template variables so personas can adapt their style.
Template variables are validated before rendering and missing fields raise
``ValueError``. Pipelines of multiple templates can be executed with
``run_pipeline()`` which optionally returns a debug trace of each step. For long
responses ``render_stream()`` yields chunks as soon as they are generated so you
can stream output to clients.

```python
from raeburn_brain.core import MemoryStore
from raeburn_brain.prompt import PromptManager

store = MemoryStore()
store.add("a1", "prior event")
mgr = PromptManager("templates", store=store)
mgr.add_history("a1", "hello there")
text = mgr.render("a1", "welcome.txt", mood="cheerful", tone="formal", name="Bob")

# stream a response to the client
for chunk in mgr.render_stream("a1", "welcome.txt", name="Bob"):
    print(chunk, end="", flush=True)

# run a two-step prompt pipeline with debugging
final, trace = mgr.run_pipeline(
    "a1",
    ["intro.txt", "summary.txt"],
    name="Bob",
    debug=True,
)
```

## Memory & Knowledge Layer

``MemoryStore`` can persist memories using different backends. Choose between
``TinyDBBackend`` for lightweight JSON storage, ``SQLiteBackend`` for a single
file database with FTS5 search, or ``PostgresBackend``/``PgvectorBackend`` for
production systems. ``FaissBackend`` provides semantic similarity search using
embeddings. Entries include tags, timestamps, and an importance score for TTL
pruning. You can also retrieve recent memories by tag using ``store.by_tag()``
to build a semantic index for quick lookups.

If you use a PostgreSQL backend the ``entries`` table is created via Alembic
migrations. ``PgvectorBackend`` stores an ``embedding`` vector column to enable
semantic similarity queries with ``pgvector``.

```python
from raeburn_brain.core import MemoryStore
from raeburn_brain.memory import SQLiteBackend

store = MemoryStore(SQLiteBackend("mem.db"))
store.add("agent", "important fact", tags=["core"], importance=0.9)
store.add("agent", "throwaway", importance=0.1)
hits = store.search("agent", "important")
store.prune("agent", threshold=0.5)

# semantic search
sim = store.similar("agent", "important fact")
# tag-based retrieval
core_memories = store.by_tag("agent", "core")
```

Logs can be ingested directly as memory entries. ``ingest_logs`` reads JSON or
plain-text lines and stores them for semantic search. Parsed tags from the log
become part of the tagging index so you can fetch them via ``store.by_tag``.
Periodic pruning jobs remove low-importance or expired memories:

```python
from raeburn_brain.memory import ingest_logs

ingest_logs(store, "server.log", agent_id="agent")
store.start_pruner("agent", interval=3600, ttl=86400)
```

## Agent Lifecycle Management

Agents are persisted in a database table managed by Alembic migrations. Use
`run_migrations()` on startup to create or upgrade the schema. The
`AgentRegistry` interacts with this table to store performance stats, mentor
links, and clones.

`ensure()` creates a new agent with generated persona traits. `mentor()` links
two agents and `clone()` creates a new agent inheriting the parent's persona and
setting the mentor field.

```python
from raeburn_brain.agent import AgentRegistry
from raeburn_brain.db import run_migrations

run_migrations()
registry = AgentRegistry()
agent = registry.ensure("alice", ["brave", "curious"])
for _ in range(5):
    registry.record("alice", True)
assert agent.title == "promoted"
registry.ensure("bob", ["wise"])
registry.mentor("alice", "bob")
clone = registry.clone("alice", "alice_clone")
assert clone.mentor_id == "alice"
```

## Meta-Agent Scheduler

`MetaAgentScheduler` assigns daily missions and evaluates agents using logs and
model metrics. Mission outcomes are persisted so scores can be adjusted over
time. The scheduler runs asynchronously using `asyncio`.

```python
from raeburn_brain.meta import MetaAgentScheduler, MissionOutcomeStore
from raeburn_brain.core import MemoryStore
from raeburn_brain.model import ModelMetricsStore

run_migrations()
registry = AgentRegistry()
store = MemoryStore()
metrics = ModelMetricsStore()
outcomes = MissionOutcomeStore()

sched = MetaAgentScheduler(registry, store, metrics=metrics, outcomes=outcomes, interval=3600)
sched.perform_daily()  # or sched.start() to run continuously
```


## Configuration

Runtime settings are loaded with Pydantic. Copy `.env.example` to `.env` and adjust the values or set environment variables directly. Key options include:

```bash
# database connection
RAEBURN_DATABASE_URL=sqlite:///raeburn.db
# logging level
RAEBURN_LOG_LEVEL=INFO
# enable debug mode
RAEBURN_DEBUG=false
# configuration signature verification
RAEBURN_CONFIG_SIGNATURE=abcdef
```

Set `RAEBURN_CONFIG_FILE` to point to a custom env file if you want to load configuration from a different location.


## Development Setup

Install editable package for local development:

```bash
python -m pip install -e .
```

Run tests with:

```bash
pytest
```

Integration tests cover asynchronous memory operations and the router's
hybrid fallback logic to ensure end-to-end functionality.

## Containerization & Secure Deployment

Build a Docker image and run the service with dashboard authentication:

```bash
docker build -t raeburn-brain .
docker run -p 8080:8080 \
  -e RAEBURN_DASHBOARD_TOKEN=secret \
  -e RAEBURN_OAUTH_USER=admin \
  -e RAEBURN_OAUTH_PASS=password \
  -e RAEBURN_CONFIG_SECRET=changeme \
  -e RAEBURN_CONFIG_SIGNATURE=abcdef \
  -e RAEBURN_TLS_CERTFILE=/certs/cert.pem \
  -e RAEBURN_TLS_KEYFILE=/certs/key.pem \
  raeburn-brain
```

The container image runs under a dedicated non-root user with a read-only root
filesystem and no Linux capabilities for better isolation. TLS termination is
handled by an Ingress managed by cert-manager, and sensitive values like
dashboard credentials are injected from Kubernetes Secrets so they can be
rotated independently of deployments.

The `deploy/raeburn-brain.service` unit can be installed with systemd. It loads
environment variables from `/etc/raeburn/env`.

Set `RAEBURN_CONFIG_SECRET` and `RAEBURN_CONFIG_SIGNATURE` to verify the
configuration signature at startup.

## Continuous Integration

GitHub Actions runs linting, type checks, tests, and builds the container image.
It scans the image with both Trivy and Grype, lints the Helm chart, and synchronizes Argo CD environments. Pull requests and pushes to `main` deploy to `raeburn-brain-staging`, while tagged releases promote `raeburn-brain-prod`.
The workflow is defined in `.github/workflows/ci.yml` and executes roughly:

```yaml
- uses: actions/setup-python@v5
- run: ruff raeburn_brain tests
- run: mypy raeburn_brain
- run: pytest -q
- run: docker build -t ghcr.io/$REPO:$SHA .
- uses: aquasecurity/trivy-action@v0.19.0
  with:
    image-ref: ghcr.io/$REPO:$SHA
- uses: anchore/scan-action@v3
  with:
    image: ghcr.io/$REPO:$SHA
- run: helm lint helm/raeburn-brain
- run: argocd app sync raeburn-brain-staging
- run: argocd app sync raeburn-brain-prod
```

Store your Argo CD credentials in the repository secrets `ARGOCD_SERVER`,
`ARGOCD_USERNAME`, and `ARGOCD_PASSWORD` to enable automatic deployment.

