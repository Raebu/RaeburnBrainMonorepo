from BusinessFactory.reorg_engine import reassign_agent


def test_reassign_agent_moves_between_businesses():
    mapping = {"biz1": ["a1", "a2"], "biz2": ["b1"]}
    updated = reassign_agent(mapping, "a2", "biz2")
    assert "a2" not in updated["biz1"]
    assert "a2" in updated["biz2"]
