# Raeburn Orchestrator
[![CI](https://github.com/owner/RaeburnOrchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/owner/RaeburnOrchestrator/actions/workflows/ci.yml)
[![Release](https://github.com/owner/RaeburnOrchestrator/actions/workflows/release.yml/badge.svg)](https://github.com/owner/RaeburnOrchestrator/actions/workflows/release.yml)
[![Coverage](https://codecov.io/gh/owner/RaeburnOrchestrator/branch/main/graph/badge.svg)](https://codecov.io/gh/owner/RaeburnOrchestrator)

A minimal demonstration of the Raeburn Orchestrator pipeline as of July 2025.

## Setup

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,lint]'
```

Run the unit tests to verify everything works:

```bash
pytest -q
pytest --cov=. --cov-report=term-missing
```

Run the linters and type checker:

```bash
ruff check .
mypy .
```
### Dependencies

See `pyproject.toml` for the exact versions. Key packages include:

- httpx - async HTTP client
- pytest - for running the tests
- ruff - code style checker
- mypy - static type checker
- OpenTelemetry SDK - optional metrics exporter



## Usage

```bash
raeburn-orchestrator "Your prompt here" --agent copywriter
```

To run the orchestrator as an API server with FastAPI, start `uvicorn`:

```bash
uvicorn raeburn_brain.orchestrator.api:app --reload
```

POST `/orchestrate` with a JSON body matching the `Task` fields to receive the
pipeline result.

You can also construct a `Task` dataclass for structured calls:

```python
from raeburn_brain.orchestrator.task import Task
task = Task(user_input="Compose an email", agent_role="copywriter", priority=2)
```

Memory records are validated with a `MemoryRecord` model before being saved:

```python
from core.memory_record import MemoryRecord
rec = MemoryRecord(input="hi", output="hello")
```

### Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `RAEBURN_ORCHESTRATOR_MODE` | `prod`, `test`, or `dry-run` to control persistence and logging | `prod` |
| `RAEBURN_ORCHESTRATOR_PARALLEL` | Set to `1` or `true` to enable parallel model routing | `0` |
| `RAEBURN_ORCHESTRATOR_MEMORY_LIMIT` | Number of past memories to inject into prompts | `5` |
| `RAEBURN_MEMORY_PATH` | File path where memories are stored | `logs/memory.log` |
| `RAEBURN_LOG_PATH` | Directory where orchestrator and quality logs are written | `logs` |
| `RAEBURN_LOG_MAX_BYTES` | Rotate log files when they exceed this size in bytes | `5000000` |
| `RAEBURN_LOG_STREAM_URL` | Optional HTTP endpoint to stream log lines | - |
| `RAEBURN_OTEL_EXPORTER_URL` | Optional OTLP endpoint for OpenTelemetry metrics | - |
| `RAEBURN_OTEL_TRACE_URL` | Optional OTLP endpoint for OpenTelemetry traces | - |
| `RAEBURN_AGENT_CONFIG` | Optional JSON file describing available agents (validated) | - |
| `RAEBURN_DB_PATH` | Optional SQLite DB file for memories and logs (uses WAL and transactions) | - |
| `RAEBURN_DB_URL` | Optional Postgres connection URL for storing memories (uses pooling) | - |
| `RAEBURN_PG_POOL_MIN_SIZE` | Minimum connections in the Postgres pool | `1` |
| `RAEBURN_PG_POOL_MAX_SIZE` | Maximum connections in the Postgres pool | `10` |
| `RAEBURN_VECTOR_URL` | Optional Qdrant URL for vector search | - |
| `RAEBURN_VECTOR_COLLECTION` | Qdrant collection name | `memories` |

| `OPENROUTER_API_KEY` | API key for OpenRouter | - |
| `OPENROUTER_MODEL` | Default OpenRouter model | `mistralai/mistral-7b-instruct` |
| `HF_API_TOKEN` | Hugging Face API token | - |
| `HF_MODEL` | Default Hugging Face model | `google/flan-t5-small` |
| `OPENAI_API_KEY` | API key for OpenAI | - |
| `OPENAI_MODEL` | Default OpenAI model | `gpt-3.5-turbo` |
| `RAEBURN_ROUTER_CONFIG` | Optional JSON file listing providers and call paths | - |
| `RAEBURN_ROUTER_PROVIDERS` | Comma-separated provider names used when no config file is supplied | `openrouter,huggingface,openai` |
| `RAEBURN_ROUTER_TIMEOUT` | Seconds before router calls are cancelled | `60` |
| `RAEBURN_SCORING_BACKEND` | `embedding` or `model` for advanced scoring | `rule` |
| `RAEBURN_EMBEDDING_MODEL` | Name of the sentence-transformers model | `all-MiniLM-L6-v2` |
| `RAEBURN_SCORE_WEIGHTS` | JSON or comma list of weights for length, keyword, similarity, latency | `0.15,0.25,0.45,0.15` |
| `RAEBURN_SCORING_PLUGIN` | Optional dotted path to a custom scoring function | - |
| `RAEBURN_JUDGE_BACKEND` | `rule` or `model` judge selection | `rule` |
| `RAEBURN_FEEDBACK_WEIGHT` | Weight for user feedback in scoring | `0.2` |

Provider API keys should be supplied via environment variables. In CI or
production deployments, configure these variables through GitHub Secrets or a
secret management tool such as Vault so credentials are not stored in the
repository.

When `RAEBURN_DB_PATH` is set, memories and logs are stored in a SQLite database
using write-ahead logging and FTS indexing. You can instead set
`RAEBURN_DB_URL` to point at a Postgres instance. Each operation executes within
a transaction so concurrent orchestrations can safely read and write memories.
The Postgres backend now uses a connection pool so repeated operations reuse
the same connections. Configure the pool size with `RAEBURN_PG_POOL_MIN_SIZE`
and `RAEBURN_PG_POOL_MAX_SIZE` if needed.

If `RAEBURN_VECTOR_URL` is provided, memories are indexed in a Qdrant collection
for semantic search. The collection name defaults to `RAEBURN_VECTOR_COLLECTION`
(`memories`). Records are upserted with embeddings from the configured model and
queries use vector similarity to fetch relevant memories first.

Router behavior can be customized via `RAEBURN_ROUTER_CONFIG`. The file should
list providers and optionally the import path to their call functions. If not
set, `RAEBURN_ROUTER_PROVIDERS` selects which of the built-in providers are
used. All provider requests employ exponential backoff with `tenacity`.

### Task Priority

Add a `priority` field to the task JSON when invoking the orchestrator. A
priority greater than `1` automatically enables parallel model routing,
even if `RAEBURN_ORCHESTRATOR_PARALLEL` is unset. The priority value is
stored alongside each memory record for later analysis.

### Scoring Algorithm

Candidate responses are ranked using a weighted blend of response
length, keyword overlap, semantic similarity, and latency. The
similarity check defaults to a simple string matcher but can be
upgraded to sentence embeddings or model-based ranking by setting
`RAEBURN_SCORING_BACKEND=embedding` or `model`. When embedding mode is enabled the
embedding model specified by `RAEBURN_EMBEDDING_MODEL` (default
`all-MiniLM-L6-v2`) is used to compute cosine similarity.
You can supply your own scoring logic by pointing `RAEBURN_SCORING_PLUGIN`
at a Python function. Scores can also incorporate user feedback using the
`RAEBURN_FEEDBACK_WEIGHT` variable.
Setting `RAEBURN_JUDGE_BACKEND=model` will ask a language model to choose the
best candidate among all responses.

Weights for the scoring components can be customised via the
`RAEBURN_SCORE_WEIGHTS` environment variable. Provide a JSON object or
comma separated list of four numbers representing the weights for
length, keyword matches, similarity, and latency. The values are
normalised automatically.

### Agent Configuration

Define custom agents by pointing `RAEBURN_AGENT_CONFIG` to a JSON file. Each
entry should include a `name` and optional metadata like `system_prompt`,
`prompt_style`, `capabilities`, or `model_preferences`. The file is validated
using [Pydantic](https://docs.pydantic.dev) so invalid entries are ignored.

Agents may also be registered dynamically at runtime using
`agents.register_agent(role, **fields)` which validates the fields with the same
schema. Call `list_agents()` to inspect the currently available roles.

Example `agents.json`:

```json
{
  "analyst": {"name": "analyst", "system_prompt": "You analyze data."}
}
```

Use `list_agents()` from `identity_engine` to see which roles are available.

### Log Format

Each run writes a JSON line to `logs/orchestrator.log` when the pipeline completes:

```json
{
  "timestamp": "2025-07-13T19:30:55Z",
  "agent": "insight_scout",
  "model_used": "mistral-openrouter",
  "input": "What startup should I build for solo founders?",
  "score": 0.91,
  "session": "sess_f4kL23Mx",
  "duration_ms": 3922,
  "mode": "prod"
}
```

Model quality metrics are recorded asynchronously in `logs/quality.log` using a
similar JSON structure:

```json
{
  "timestamp": "2025-07-13T19:30:55Z",
  "model": "mistral-openrouter",
  "score": 0.91,
  "session": "sess_f4kL23Mx"
}
```

Logs are written asynchronously with [structlog](https://www.structlog.org/) and
rotated once the file exceeds `RAEBURN_LOG_MAX_BYTES`. Set `RAEBURN_LOG_STREAM_URL`
to POST each entry to an external observability endpoint. When `RAEBURN_OTEL_EXPORTER_URL`
is defined, metrics for each event and quality score are sent using [OpenTelemetry](https://opentelemetry.io/)
over OTLP. Set `RAEBURN_OTEL_TRACE_URL` to export tracing spans for router and
orchestrator calls.

## Releases

Tagged pushes trigger a workflow that builds the package, signs the artifacts
with a GPG key, uploads them to PyPI, and then attaches the wheels to a GitHub
Release.  Set the `PYPI_TOKEN` and `GPG_PRIVATE_KEY` secrets in the repository
to enable publishing.  The release badge at the top of this file reflects the
latest published version.

## License

This project is released under the [MIT License](LICENSE).

