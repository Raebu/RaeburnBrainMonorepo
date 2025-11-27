from __future__ import annotations

"""Model infrastructure with pluggable fetchers and health scoring."""

from dataclasses import dataclass
from random import random
from time import perf_counter, sleep, time
from typing import Dict, Iterable, Sequence, Tuple
import hmac
import hashlib
import os
import sqlite3
import httpx
from prometheus_client import Histogram
try:
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional
    openai = None

MODEL_LATENCY = Histogram("model_latency_seconds", "Model inference latency", ["model"])  # noqa: E501
MODEL_COST = Histogram("model_cost_dollars", "Model cost in dollars", ["model"])


@dataclass
class FetcherStats:
    """Health metrics for a model fetcher."""

    name: str
    cost: float
    latency: float
    accuracy: float

    def score(self) -> float:
        """Composite score balancing accuracy against cost and latency."""
        return self.accuracy - self.cost - self.latency


class ModelMetricsStore:
    """Persist model metrics to an SQLite database."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS metrics (model TEXT, latency REAL, cost REAL, ts REAL)"
        )
        self.conn.commit()

    def record(self, model: str, latency: float, cost: float) -> None:
        self.conn.execute(
            "INSERT INTO metrics (model, latency, cost, ts) VALUES (?, ?, ?, ?)",
            (model, latency, cost, time()),
        )
        self.conn.commit()

    def all(self) -> Iterable[tuple[str, float, float]]:
        cur = self.conn.execute("SELECT model, latency, cost FROM metrics")
        return cur.fetchall()


class BaseModelFetcher:
    """Base interface for model fetchers."""

    def __init__(self, name: str, cost: float = 0.0) -> None:
        self.name = name
        self.cost = cost

    def generate(self, prompt: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def probe(self) -> FetcherStats:
        """Run a synthetic probe and collect metrics."""
        start = perf_counter()
        output = self.generate("__probe__")
        latency = perf_counter() - start
        accuracy = 1.0 if "__probe__" in output else 0.0
        return FetcherStats(self.name, self.cost, latency, accuracy)


class CachedModelFetcher(BaseModelFetcher):
    """Wrap another fetcher with an in-memory cache."""

    def __init__(self, fetcher: BaseModelFetcher, ttl: float = 60.0) -> None:
        super().__init__(fetcher.name, fetcher.cost)
        self.fetcher = fetcher
        self.ttl = ttl
        self.cache: Dict[str, Tuple[float, str]] = {}

    def generate(self, prompt: str) -> str:
        now = time()
        if prompt in self.cache:
            ts, val = self.cache[prompt]
            if now - ts < self.ttl:
                return val
        val = self.fetcher.generate(prompt)
        self.cache[prompt] = (now, val)
        return val

    def probe(self) -> FetcherStats:
        return self.fetcher.probe()


class LocalModelFetcher(BaseModelFetcher):
    """Simple local model with optional signature verification."""

    def __init__(
        self,
        path: str,
        *,
        url: str | None = None,
        signature: str | None = None,
        secret: str | None = None,
        cost: float = 0.0,
    ) -> None:
        super().__init__(name=path, cost=cost)
        self.path = path
        self.url = url
        self.signature = signature
        self.secret = secret
        if url and not os.path.exists(path):
            self._download()

    def _download(self) -> None:
        if not (self.url and self.signature and self.secret):
            raise ValueError("download requires url, signature and secret")
        with httpx.Client(follow_redirects=True) as client:
            r = client.get(self.url)
            r.raise_for_status()
            data = r.content
        digest = hmac.new(self.secret.encode(), data, hashlib.sha256).hexdigest()
        if digest != self.signature:
            raise SystemExit("model signature mismatch")
        with open(self.path, "wb") as f:
            f.write(data)

    def _verify(self) -> None:
        if self.signature and self.secret:
            data = open(self.path, "rb").read()
            digest = hmac.new(self.secret.encode(), data, hashlib.sha256).hexdigest()
            if digest != self.signature:
                raise SystemExit("model signature mismatch")

    def generate(self, prompt: str) -> str:
        self._verify()
        return f"local:{prompt}"


class RemoteModelFetcher(BaseModelFetcher):
    """Remote model accessed via HTTP-like call."""

    def __init__(
        self,
        endpoint: str,
        *,
        cost: float = 0.01,
        api_key: str | None = None,
    ) -> None:
        super().__init__(name=endpoint, cost=cost)
        self.endpoint = endpoint
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        start = perf_counter()
        with httpx.Client() as client:
            r = client.post(self.endpoint, json={"prompt": prompt}, headers=headers)
            r.raise_for_status()
        latency = perf_counter() - start
        MODEL_LATENCY.labels(self.name).observe(latency)
        # naive token estimation
        tokens = len(prompt.split())
        MODEL_COST.labels(self.name).observe(self.cost * tokens / 1000)
        try:
            return r.json().get("text", "")
        except Exception:
            return r.text


class OpenAIModelFetcher(RemoteModelFetcher):
    """Fetcher using the official OpenAI client."""

    def __init__(self, model: str, api_key: str, cost: float = 0.0) -> None:
        super().__init__(f"openai:{model}", cost=cost)
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        if openai is None:  # pragma: no cover - library missing
            raise RuntimeError("openai package not available")
        start = perf_counter()
        openai.api_key = self.api_key
        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = perf_counter() - start
        text = resp.choices[0].message["content"]
        tokens = resp.usage.total_tokens if hasattr(resp, "usage") else len(prompt.split())
        MODEL_LATENCY.labels(self.name).observe(latency)
        MODEL_COST.labels(self.name).observe(self.cost * tokens / 1000)
        return text


class ClaudeModelFetcher(RemoteModelFetcher):
    """Simple fetcher for Claude via HTTP."""

    def __init__(self, model: str, api_key: str, cost: float = 0.0) -> None:
        endpoint = "https://api.anthropic.com/v1/complete"
        super().__init__(endpoint, cost=cost, api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
        }
        start = perf_counter()
        with httpx.Client() as client:
            r = client.post(
                self.endpoint,
                headers=headers,
                json={"model": self.model, "prompt": prompt, "max_tokens": 1},
            )
            r.raise_for_status()
            data = r.json()
        latency = perf_counter() - start
        MODEL_LATENCY.labels(self.name).observe(latency)
        tokens = data.get("usage", {}).get("total_tokens", len(prompt.split()))
        MODEL_COST.labels(self.name).observe(self.cost * tokens / 1000)
        return data.get("completion", "")


class OpenAIHTTPFetcher(BaseModelFetcher):
    """Use httpx to call OpenAI's chat completion API."""

    def __init__(self, model: str, api_key: str, *, cost: float = 0.0, url: str | None = None) -> None:
        super().__init__(name=f"openai:{model}", cost=cost)
        self.model = model
        self.api_key = api_key
        self.url = url or "https://api.openai.com/v1/chat/completions"

    def generate(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        start = perf_counter()
        with httpx.Client() as client:
            r = client.post(
                self.url,
                headers=headers,
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            data = r.json()
        latency = perf_counter() - start
        MODEL_LATENCY.labels(self.name).observe(latency)
        tokens = data.get("usage", {}).get("total_tokens", len(prompt.split()))
        MODEL_COST.labels(self.name).observe(self.cost * tokens / 1000)
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        return message.get("content", "")


class HuggingFaceFetcher(BaseModelFetcher):
    """Call the HuggingFace Inference API using httpx."""

    def __init__(self, model: str, *, api_key: str | None = None, cost: float = 0.0) -> None:
        super().__init__(name=f"hf:{model}", cost=cost)
        self.model = model
        self.api_key = api_key
        self.url = f"https://api-inference.huggingface.co/models/{model}"

    def generate(self, prompt: str) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        start = perf_counter()
        with httpx.Client() as client:
            r = client.post(self.url, headers=headers, json={"inputs": prompt})
            r.raise_for_status()
            data = r.json()
        latency = perf_counter() - start
        MODEL_LATENCY.labels(self.name).observe(latency)
        tokens = len(prompt.split())
        if isinstance(data, list) and data:
            tokens += len(data[0].get("generated_text", "").split())
        elif isinstance(data, dict):
            tokens += len(data.get("generated_text", "").split())
        MODEL_COST.labels(self.name).observe(self.cost * tokens / 1000)
        if isinstance(data, list):
            return data[0].get("generated_text", "")
        return data.get("generated_text", "")


class ModelRegistry:
    """Track multiple fetchers and choose the best one."""

    def __init__(
        self,
        fetchers: Sequence[BaseModelFetcher],
        *,
        metrics: ModelMetricsStore | None = None,
    ) -> None:
        self.fetchers = list(fetchers)
        self.stats: Dict[str, FetcherStats] = {}
        self.metrics = metrics

    def refresh(self) -> None:
        for fetcher in self.fetchers:
            stat = fetcher.probe()
            self.stats[fetcher.name] = stat
            if self.metrics:
                self.metrics.record(stat.name, stat.latency, stat.cost)

    def best(self) -> BaseModelFetcher:
        self.refresh()
        return max(self.fetchers, key=lambda f: self.stats[f.name].score())

    def generate(self, prompt: str) -> str:
        """Generate a response using the best-scoring fetcher."""
        fetcher = self.best()
        return fetcher.generate(prompt)


__all__ = [
    "FetcherStats",
    "BaseModelFetcher",
    "LocalModelFetcher",
    "RemoteModelFetcher",
    "CachedModelFetcher",
    "OpenAIModelFetcher",
    "OpenAIHTTPFetcher",
    "HuggingFaceFetcher",
    "ClaudeModelFetcher",
    "ModelMetricsStore",
    "ModelRegistry",
]
