import asyncio
import importlib
import json
import os
import time
from typing import Any, Callable, MutableMapping, cast

import aiofiles  # type: ignore
import aiosqlite  # type: ignore
import httpx
import structlog
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential
from utils.logging import (
    log_event,
    _rotate,
    logger,
    OTEL_QUALITY_HIST,
)
from utils.tracing import tracer, async_span


def _get_providers() -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Callable]]:
    """Load provider configuration from environment or config file."""
    path = os.getenv("RAEBURN_ROUTER_CONFIG")
    default_funcs: dict[str, Callable] = {
        "openrouter": _call_openrouter,  # type: ignore[name-defined]
        "huggingface": _call_huggingface,  # type: ignore[name-defined]
        "openai": _call_openai,  # type: ignore[name-defined]
    }
    if path and os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        providers = data.get("providers", [])
        names: list[str] = []
        configs: dict[str, dict[str, Any]] = {}
        funcs: dict[str, Callable] = {}
        for p in providers:
            if isinstance(p, str):
                name = p
                cfg: dict[str, Any] = {}
                call_path = None
            else:
                name = p.get("name")
                cfg = p
                call_path = p.get("call")
            if not name:
                continue
            names.append(name)
            configs[name] = cfg
            if call_path:
                module, func_name = call_path.rsplit(".", 1)
                func = getattr(importlib.import_module(module), func_name)
                funcs[name] = func
            elif name in default_funcs:
                funcs[name] = default_funcs[name]
        return names, configs, funcs

    names = [p.strip() for p in os.getenv("RAEBURN_ROUTER_PROVIDERS", "openrouter,huggingface,openai").split(",") if p.strip()]
    if not names:
        names = ["openrouter", "huggingface", "openai"]
    return names, {}, default_funcs

async def _call_openrouter(
    prompt: str, session_id: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call a model through the OpenRouter API with retries or return a mock."""
    config = config or {}
    model = config.get("model") or os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
    api_key = config.get("api_key") or os.getenv("OPENROUTER_API_KEY")
    start = time.monotonic()
    async with async_span("openrouter", tracer):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://example.com",
            "X-Title": "RaeburnOrchestrator",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if not api_key:
            return {
                "id": "openrouter-mock",
                "model": model,
                "content": prompt + " - openrouter",
                "latency": int((time.monotonic() - start) * 1000),
                "error": "missing_api_key",
            }

        error = None
        content = ""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            json=payload,
                            headers=headers,
                        )
                        resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            if isinstance(e, RetryError):
                error = str(e.last_attempt.exception())
            else:
                error = str(e)
            await log_event(
                "router_error",
                {"provider": "openrouter", "session": session_id, "error": error},
            )
        latency = int((time.monotonic() - start) * 1000)
        return {
            "id": "openrouter",
            "model": model,
            "content": content,
            "latency": latency,
            "error": error,
        }


async def _call_openai(
    prompt: str, session_id: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call OpenAI Chat API with retries or return a mock."""
    config = config or {}
    model = config.get("model") or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
    start = time.monotonic()
    async with async_span("openai", tracer):
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if not api_key:
            return {
                "id": "openai-mock",
                "model": model,
                "content": prompt + " - openai",
                "latency": int((time.monotonic() - start) * 1000),
                "error": "missing_api_key",
            }

        error = None
        content = ""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            json=payload,
                            headers=headers,
                        )
                        resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            if isinstance(e, RetryError):
                error = str(e.last_attempt.exception())
            else:
                error = str(e)
            await log_event(
                "router_error", {"provider": "openai", "session": session_id, "error": error}
            )
        latency = int((time.monotonic() - start) * 1000)
        return {
            "id": "openai",
            "model": model,
            "content": content,
            "latency": latency,
            "error": error,
        }


async def _call_huggingface(
    prompt: str, session_id: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call HuggingFace inference API with retries or return a mock."""
    config = config or {}
    model = config.get("model") or os.getenv("HF_MODEL", "google/flan-t5-small")
    token = config.get("token") or os.getenv("HF_API_TOKEN")
    start = time.monotonic()
    async with async_span("huggingface", tracer):
        headers = {"Authorization": f"Bearer {token}"}
        if not token:
            return {
                "id": "huggingface-mock",
                "model": model,
                "content": prompt + " - huggingface",
                "latency": int((time.monotonic() - start) * 1000),
                "error": "missing_api_token",
            }

        error = None
        content = ""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5)
                ):
                    with attempt:
                        resp = await client.post(
                            f"https://api-inference.huggingface.co/models/{model}",
                            headers=headers,
                            json={"inputs": prompt},
                        )
                        resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                content = data[0].get("generated_text", "")
            else:
                content = data.get("generated_text", "")
        except Exception as e:  # noqa: BLE001
            if isinstance(e, RetryError):
                error = str(e.last_attempt.exception())
            else:
                error = str(e)
            await log_event(
                "router_error",
                {"provider": "huggingface", "session": session_id, "error": error},
            )
        latency = int((time.monotonic() - start) * 1000)
        return {
            "id": "huggingface",
            "model": model,
            "content": content,
            "latency": latency,
            "error": error,
        }


async def route_prompt(
    prompt: str,
    agent: dict,
    session_id: str,
    parallel: bool = False,
    priority: int = 1,
) -> list[dict]:
    """Route the prompt through multiple providers."""
    async with async_span(
        "route_prompt", tracer, attributes={"parallel": parallel, "priority": priority}
    ):
        names, configs, funcs = _get_providers()
        timeout = float(os.getenv("RAEBURN_ROUTER_TIMEOUT", "60"))
        tasks: list[asyncio.Task] = []
        used_names: list[str] = []
        for name in names:
            func = funcs.get(name)
            if func:
                used_names.append(name)
                coro = func(prompt, session_id, configs.get(name, {}))
                task = asyncio.create_task(asyncio.wait_for(coro, timeout=timeout))
                tasks.append(task)
        results: list[dict[str, Any]] = []
        if parallel:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            responses = []
            for t in tasks:
                try:
                    responses.append(await t)
                except Exception as exc:  # noqa: BLE001
                    responses.append(exc)
        for name, r in zip(used_names, responses):
            if isinstance(r, Exception):
                await log_event("router_error", {"provider": name, "session": session_id, "error": str(r)})
            else:
                results.append(cast(dict[str, Any], r))
        if not results:
            results.append(
                {
                    "id": "fallback",
                    "model": "fallback",
                    "content": prompt,
                    "latency": 0,
                    "error": "no_providers_succeeded",
                }
            )
        return results


async def record_quality(model: str, score: float, session_id: str) -> None:
    """Persist model quality metrics asynchronously with rotation and streaming."""
    record: MutableMapping[str, Any] = {
        "model": model,
        "score": score,
        "session": session_id,
    }
    stamp = structlog.processors.TimeStamper(key="timestamp", fmt="iso", utc=True)
    record = cast(MutableMapping[str, Any], stamp(logger, "info", record))
    json_line = structlog.processors.JSONRenderer()(logger, "info", record)

    if OTEL_QUALITY_HIST is not None:
        OTEL_QUALITY_HIST.record(score, {"model": model})

    db_path = os.getenv("RAEBURN_DB_PATH")
    if db_path:
        try:
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS quality_logs (json TEXT)"
                )
                await db.execute("INSERT INTO quality_logs (json) VALUES (?)", (json_line,))
                await db.commit()
            return
        except Exception as exc:  # noqa: BLE001
            await log_event(
                "quality_log_error", {"session": session_id, "error": str(exc)}
            )
            raise

    log_dir = os.getenv("RAEBURN_LOG_PATH", "logs")
    os.makedirs(log_dir, exist_ok=True)
    max_bytes = int(os.getenv("RAEBURN_LOG_MAX_BYTES", "5000000"))
    path = os.path.join(log_dir, "quality.log")
    await _rotate(path, max_bytes)
    try:
        async with aiofiles.open(path, "a") as f:
            await f.write(str(json_line) + "\n")
    except Exception as exc:  # noqa: BLE001
        await log_event(
            "quality_log_error", {"session": session_id, "error": str(exc)}
        )
        raise

    stream_url = os.getenv("RAEBURN_LOG_STREAM_URL")
    if stream_url:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(stream_url, json=json.loads(json_line))

