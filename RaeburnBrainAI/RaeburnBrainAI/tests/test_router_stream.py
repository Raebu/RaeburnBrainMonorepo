import asyncio

from RaeburnBrainAI.router_stream import stream


def test_router_stream_yields_content():
    async def _collect():
        outputs = []
        async for chunk in stream("hi", session_id="stream-test"):
            outputs.append(chunk)
        return outputs

    outputs = asyncio.run(_collect())
    assert outputs
