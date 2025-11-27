import pytest
import httpx

from raeburn_brain.comm import (
    TelegramAdapter,
    TelegramBot,
    SlackAdapter,
    DiscordAdapter,
    VoicePipeline,
)


@pytest.mark.asyncio
async def test_adapters_send():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        payload = _json.loads(request.content.decode()) if request.content else {}
        requests.append((request.url.path, payload))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://example.com")

    tele = TelegramAdapter("T", client)
    slack = SlackAdapter("S", client)
    disc = DiscordAdapter("D", client)

    await tele.send_message("c1", "hello")
    await slack.send_message("c2", "hi")
    await disc.send_message("c3", "hey")

    assert requests[0][1]["text"] == "hello"
    assert requests[1][1]["text"] == "hi"
    assert requests[2][1]["content"] == "hey"


@pytest.mark.asyncio
async def test_voice_pipeline_missing_deps():
    vp = VoicePipeline()
    with pytest.raises(RuntimeError):
        await vp.transcribe("none.wav")
    gen = vp.tts_stream("hi")
    with pytest.raises(RuntimeError):
        await gen.__anext__()


@pytest.mark.asyncio
async def test_telegram_bot_commands():
    requests = []
    updates = {
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {"chat": {"id": "c1"}, "text": "/echo hi"},
            }
        ],
    }

    async def handler(req: httpx.Request) -> httpx.Response:
        import json as _json

        if req.url.path.endswith("/getUpdates"):
            data = updates.copy()
            updates["result"] = []
            return httpx.Response(200, json=data)
        payload = _json.loads(req.content.decode()) if req.content else {}
        requests.append((req.url.path, payload))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://example.com")

    bot = TelegramBot("T", client)

    async def echo(arg: str) -> str:
        return arg.upper()

    bot.add_command("echo", echo)

    await bot.poll_once()

    assert requests[0][0].endswith("/sendMessage")
    assert requests[0][1]["text"] == "HI"


@pytest.mark.asyncio
async def test_broadcast_functions():
    requests = []

    async def handler(req: httpx.Request) -> httpx.Response:
        import json as _json

        payload = _json.loads(req.content.decode()) if req.content else {}
        requests.append((req.url.path, payload))
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://example.com")

    slack = SlackAdapter("S", client)
    discord = DiscordAdapter("D", client)

    await slack.broadcast(["c1", "c2"], "hello")
    await discord.broadcast(["d1", "d2"], "hi")

    assert requests[0][0].endswith("/chat.postMessage")
    assert requests[0][1]["channel"] == "c1"
    assert requests[1][1]["channel"] == "c2"
    assert requests[2][0].endswith("/channels/d1/messages")
    assert requests[3][0].endswith("/channels/d2/messages")
