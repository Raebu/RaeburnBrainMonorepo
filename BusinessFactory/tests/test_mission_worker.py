from BusinessFactory.workers.mission_worker import execute


def test_mission_worker_llm_route():
    result = execute({"action_type": "llm", "prompt": "hello"})
    assert "content" in result


def test_mission_worker_non_llm_route():
    result = execute({"action_type": "verify", "data": {"value": 1}})
    assert "status" in result
