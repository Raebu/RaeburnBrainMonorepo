import asyncio
import json
import httpx
from core.router import route_prompt, _call_huggingface, _call_openrouter, _call_openai


def test_route_prompt_mock(monkeypatch):
    # Ensure no API keys are set for deterministic mock behavior
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = asyncio.run(route_prompt("hello", {}, "sess_x", parallel=False, priority=1))
    assert len(results) == 3
    for res in results:
        assert "latency" in res
        assert res["content"]
        assert "error" in res


def test_route_prompt_parallel(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = asyncio.run(route_prompt("hi", {}, "sess_p", parallel=True, priority=1))
    assert len(results) == 3
    assert all("latency" in r for r in results)


def test_route_prompt_partial_on_failure(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("HF_API_TOKEN", "x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    async def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr("core.router._call_huggingface", boom)

    events = []
    async def capture(e, d):
        events.append((e, d))

    monkeypatch.setattr("core.router.log_event", capture)

    results = asyncio.run(route_prompt("hi", {}, "sess_fail", parallel=False, priority=1))
    assert len(results) == 2  # openrouter and openai mocks returned
    assert events and events[0][0] == "router_error"


def test_huggingface_retries_and_logs(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "t")

    calls = {
        "count": 0,
    }

    async def fail_post(*args, **kwargs):
        calls["count"] += 1
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("httpx.AsyncClient.post", fail_post)

    async def no_sleep(_):
        pass

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    events = []
    async def capture2(e, d):
        events.append(d)

    monkeypatch.setattr("core.router.log_event", capture2)

    result = asyncio.run(_call_huggingface("prompt", "sess_retry"))
    assert result["error"] == "boom"
    assert calls["count"] == 3
    assert events and events[0]["provider"] == "huggingface"


def test_route_prompt_with_config(tmp_path, monkeypatch):
    cfg = {"providers": [{"name": "huggingface"}]}
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setenv("RAEBURN_ROUTER_CONFIG", str(cfg_path))
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    results = asyncio.run(route_prompt("hi", {}, "sess_cfg"))
    assert len(results) == 1
    assert results[0]["id"].startswith("huggingface")


def test_route_prompt_timeout(monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"id": "ok", "model": "m", "content": "hi", "latency": 100, "error": None}

    monkeypatch.setattr("core.router._call_openrouter", slow)
    monkeypatch.setenv("RAEBURN_ROUTER_TIMEOUT", "0.01")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    results = asyncio.run(route_prompt("x", {}, "sess_t", parallel=False))
    assert all(r["id"] != "openrouter" for r in results)


def test_route_prompt_fallback(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    async def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr("core.router._call_openrouter", boom)
    monkeypatch.setattr("core.router._call_huggingface", boom)
    monkeypatch.setattr("core.router._call_openai", boom)

    results = asyncio.run(route_prompt("fallback", {}, "sess_f", parallel=False))
    assert len(results) == 1
    assert results[0]["id"] == "fallback"



def test_openrouter_unauthorized(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "bad")
    events = []

    async def capture(event, data):
        events.append((event, data))

    async def fake_post(*args, **kwargs):
        return httpx.Response(401, request=httpx.Request("POST", "https://openrouter.ai"))

    monkeypatch.setattr("core.router.log_event", capture)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = asyncio.run(_call_openrouter("prompt", "sess_auth"))
    assert result["error"]
    assert events and events[0][0] == "router_error"


def test_openai_unauthorized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "bad")
    events = []

    async def capture(event, data):
        events.append((event, data))

    async def fake_post(*args, **kwargs):
        return httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com"))

    monkeypatch.setattr("core.router.log_event", capture)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = asyncio.run(_call_openai("prompt", "sess_openai"))
    assert result["error"]
    assert events and events[0][0] == "router_error"


def test_router_tracing(monkeypatch):
    names = []

    class DummySpan:
        async def __aenter__(self):
            pass
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummyTracer:
        def start_as_current_span(self, name, **attrs):
            names.append(name)
            return DummySpan()

    tracer = DummyTracer()
    monkeypatch.setattr("core.router.tracer", tracer)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = asyncio.run(route_prompt("hi", {}, "sess_tr", parallel=False))
    assert results
    assert "route_prompt" in names
    assert "openrouter" in names or "openai" in names or "huggingface" in names
