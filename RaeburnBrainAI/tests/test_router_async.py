import asyncio

from RaeburnBrainAI.router import Router


def test_router_async_route():
    async def run():
        router = Router()
        responses = await router.route("hello async")
        return responses

    results = asyncio.run(run())
    assert results
    assert results[0].content
