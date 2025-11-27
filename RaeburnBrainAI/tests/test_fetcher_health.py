import asyncio

from RaeburnBrainAI.model_fetchers.base_fetcher import BaseFetcher
from RaeburnBrainAI.model.registry import ModelMeta


class DummyFetcher(BaseFetcher):
    def __init__(self, fail_once: bool = True):
        super().__init__("dummy", ModelMeta(name="dummy", provider="local"))
        self.fail_once = fail_once

    async def generate(self, prompt: str, session_id: str):
        if self.fail_once:
            self.fail_once = False
            return self._response("", 10, error="fail")
        return self._response("ok", 5, error=None)


def test_fetcher_health_and_recovery():
    fetcher = DummyFetcher()
    first = asyncio.run(fetcher.generate("ping", "s"))
    assert first["error"]
    assert fetcher.failure_count == 1
    second = asyncio.run(fetcher.generate("ping", "s"))
    assert not second["error"]
    assert fetcher.failure_count == 1  # failure count not incremented on success
    assert fetcher.health_ok is True
