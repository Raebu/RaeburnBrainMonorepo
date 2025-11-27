import asyncio

from RaeburnBrainAI.router import Router


def test_router_returns_response():
    router = Router()
    response = asyncio.run(router.route_first("hello", session_id="test"))
    assert response.content
    assert response.model
