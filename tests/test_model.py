import hmac
import hashlib
import httpx
import pytest
from raeburn_brain.model import (
    LocalModelFetcher,
    RemoteModelFetcher,
    OpenAIHTTPFetcher,
    HuggingFaceFetcher,
    CachedModelFetcher,
    FetcherStats,
    ModelRegistry,
    ModelMetricsStore,
    MODEL_LATENCY,
    MODEL_COST,
)


def test_local_vs_remote_selection(monkeypatch):
    local = LocalModelFetcher("local-model", cost=0.0)
    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def post(self, url, json=None, headers=None):
            return type(
                "R",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"text": json["prompt"]},
                },
            )()

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: DummyClient())

    remote = RemoteModelFetcher("http://remote", cost=0.1)
    registry = ModelRegistry([local, remote])
    best = registry.best()
    assert best.name == "local-model"
    # local latency should be lower than remote
    assert registry.stats["local-model"].latency <= registry.stats["http://remote"].latency


def test_remote_preferred_when_cheaper_and_fast(monkeypatch):
    local = LocalModelFetcher("local", cost=0.2)
    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def post(self, *a, **k):
            return type(
                "R",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"text": "__probe__"},
                },
            )()

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: DummyClient())

    remote = RemoteModelFetcher("http://remote", cost=0.05)
    registry = ModelRegistry([local, remote])
    best = registry.best()
    assert best.name == "http://remote"


def test_local_signature_verification(tmp_path):
    data = b"modeldata"
    path = tmp_path / "m.bin"
    path.write_bytes(data)
    key = "k"
    sig = hmac.new(key.encode(), data, hashlib.sha256).hexdigest()
    fetcher = LocalModelFetcher(str(path), signature=sig, secret=key)
    assert fetcher.generate("hi").startswith("local:")
    bad = LocalModelFetcher(str(path), signature="bad", secret=key)
    with pytest.raises(SystemExit):
        bad.generate("hi")


def test_metrics_persisted(tmp_path):
    store = ModelMetricsStore(tmp_path / "metrics.db")
    local = LocalModelFetcher("local")
    registry = ModelRegistry([local], metrics=store)
    registry.refresh()
    rows = list(store.all())
    assert rows and rows[0][0] == "local"


def test_http_fetchers_scoring(monkeypatch):
    class DummyResp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def post(self, url, headers=None, json=None):
            if "openai" in url:
                return DummyResp({
                    "choices": [{"message": {"content": "openai"}}],
                    "usage": {"total_tokens": 10},
                })
            return DummyResp([{"generated_text": "hf", "usage": {"total_tokens": 8}}])

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: DummyClient())

    openai_f = OpenAIHTTPFetcher("gpt", api_key="k", cost=0.2)
    hf_f = HuggingFaceFetcher("bert", api_key="x", cost=0.1)
    registry = ModelRegistry([openai_f, hf_f])
    best = registry.best()
    assert best is hf_f
    out = registry.generate("hi")
    assert out in {"openai", "hf"}

    # verify Prometheus histograms were updated
    labels = {s.labels["model"] for m in MODEL_LATENCY.collect() for s in m.samples if "_count" in s.name}
    assert "hf:bert" in labels and "openai:gpt" in labels
    cost_labels = {s.labels["model"] for m in MODEL_COST.collect() for s in m.samples if "_count" in s.name}
    assert "hf:bert" in cost_labels and "openai:gpt" in cost_labels


def test_fetcher_caching(monkeypatch):
    calls = []

    class DummyFetcher:
        name = "dummy"
        cost = 0.0

        def generate(self, prompt: str) -> str:
            calls.append(prompt)
            return prompt

        def probe(self):
            return FetcherStats("dummy", 0.0, 0.0, 1.0)

    cached = CachedModelFetcher(DummyFetcher(), ttl=10)
    assert cached.generate("hi") == "hi"
    assert cached.generate("hi") == "hi"
    assert len(calls) == 1

