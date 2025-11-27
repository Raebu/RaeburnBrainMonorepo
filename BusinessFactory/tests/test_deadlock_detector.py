from BusinessFactory.deadlock_detector import has_cycle


def test_detects_cycle():
    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
    assert has_cycle(graph) is True


def test_detects_acyclic():
    graph = {"a": ["b"], "b": ["c"], "c": []}
    assert has_cycle(graph) is False
