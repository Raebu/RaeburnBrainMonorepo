from __future__ import annotations

"""Async communications adapters and voice pipeline."""

from typing import AsyncGenerator, Awaitable, Callable, Dict, Iterable, Optional
import asyncio
import httpx


class TelegramAdapter:
    """Send messages to Telegram asynchronously using the Bot API."""

    def __init__(self, token: str, client: Optional[httpx.AsyncClient] = None) -> None:
        self.token = token
        if client:
            self.client = client
        else:
            self.client = httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{token}")

    async def send_message(self, chat_id: str, text: str) -> None:
        await self.client.post("/sendMessage", json={"chat_id": chat_id, "text": text})


class TelegramBot(TelegramAdapter):
    """Simple polling Telegram bot with command handlers."""

    def __init__(
        self,
        token: str,
        client: Optional[httpx.AsyncClient] = None,
        commands: Optional[Dict[str, Callable[[str], Awaitable[str]]]] = None,
    ) -> None:
        super().__init__(token, client)
        self.commands: Dict[str, Callable[[str], Awaitable[str]]] = commands or {}

    def add_command(self, name: str, handler: Callable[[str], Awaitable[str]]) -> None:
        self.commands[name] = handler

    async def poll_once(self, offset: int = 0) -> int:
        resp = await self.client.get("/getUpdates", params={"offset": offset, "timeout": 0})
        data = resp.json()
        for update in data.get("result", []):
            offset = max(offset, update["update_id"] + 1)
            message = update.get("message") or {}
            text = message.get("text", "")
            if not text.startswith("/"):
                continue
            command, *args = text[1:].split()
            handler = self.commands.get(command)
            if handler:
                reply = await handler(" ".join(args))
                if reply:
                    await self.send_message(message["chat"]["id"], reply)
        return offset

    async def run_polling(self) -> None:
        offset = 0
        while True:
            offset = await self.poll_once(offset)
            await asyncio.sleep(1)


class SlackAdapter:
    """Post messages to Slack asynchronously."""

    def __init__(self, token: str, client: Optional[httpx.AsyncClient] = None) -> None:
        headers = {"Authorization": f"Bearer {token}"}
        self.client = client or httpx.AsyncClient(base_url="https://slack.com/api", headers=headers)

    async def send_message(self, channel: str, text: str) -> None:
        await self.client.post("/chat.postMessage", json={"channel": channel, "text": text})

    async def broadcast(self, channels: Iterable[str], text: str) -> None:
        for ch in channels:
            await self.send_message(ch, text)


class DiscordAdapter:
    """Send messages to Discord channels asynchronously."""

    def __init__(self, token: str, client: Optional[httpx.AsyncClient] = None) -> None:
        headers = {"Authorization": f"Bot {token}"}
        self.client = client or httpx.AsyncClient(base_url="https://discord.com/api", headers=headers)

    async def send_message(self, channel_id: str, text: str) -> None:
        await self.client.post(f"/channels/{channel_id}/messages", json={"content": text})

    async def broadcast(self, channels: Iterable[str], text: str) -> None:
        for ch in channels:
            await self.send_message(ch, text)


class VoicePipeline:
    """Speech recognition and TTS using Whisper and gTTS with async streaming."""

    def __init__(self, model: str = "base") -> None:
        try:
            import whisper  # type: ignore
        except Exception:  # pragma: no cover - optional dep
            whisper = None
        self._whisper = whisper
        self._model_name = model
        self._model = whisper.load_model(model) if whisper else None

    async def transcribe(self, audio_path: str) -> str:
        """Return text from audio using Whisper if installed."""
        if not self._whisper:
            raise RuntimeError("whisper not installed")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self._model.transcribe(audio_path))
        return result.get("text", "")

    async def tts_stream(self, text: str, lang: str = "en") -> AsyncGenerator[bytes, None]:
        """Yield synthesized speech as a stream of bytes."""
        try:
            from gtts import gTTS  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dep
            raise RuntimeError("gTTS not installed") from exc

        import io

        loop = asyncio.get_event_loop()

        def synth() -> bytes:
            tts = gTTS(text=text, lang=lang)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()

        data = await loop.run_in_executor(None, synth)
        chunk_size = 1024
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]


__all__ = [
    "TelegramAdapter",
    "TelegramBot",
    "SlackAdapter",
    "DiscordAdapter",
    "VoicePipeline",
]
