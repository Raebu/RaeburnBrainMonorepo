import asyncio
from core.judge import judge_outputs


def test_judge_ranks_candidates():
    candidates = [
        {"id": "a", "content": "short answer", "model": "m1", "latency": 10, "error": None},
        {"id": "b", "content": "This is a much longer answer containing the keyword magic", "model": "m2", "latency": 15, "error": None},
        {"id": "c", "content": "", "model": "m3", "latency": 5, "error": "oops"},
    ]
    best, scores = asyncio.run(judge_outputs(candidates, "Tell me some magic"))
    assert best["id"] == "b"
    assert scores["b"] > scores["a"]
    assert scores["c"] == 0


def test_judge_uses_similarity():
    candidates = [
        {
            "id": "a",
            "content": "Quantum computers use qubits",
            "model": "m1",
            "latency": 10,
            "error": None,
        },
        {
            "id": "b",
            "content": "Explain quantum computing using qubits",
            "model": "m2",
            "latency": 15,
            "error": None,
        },
    ]
    best, scores = asyncio.run(judge_outputs(candidates, "Explain quantum computing"))
    assert best["id"] == "b"
    assert scores["b"] > scores["a"]


def test_judge_penalizes_latency():
    candidates = [
        {"id": "a", "content": "same", "model": "m1", "latency": 1000, "error": None},
        {"id": "b", "content": "same", "model": "m2", "latency": 50, "error": None},
    ]
    best, scores = asyncio.run(judge_outputs(candidates, "Hi"))
    assert best["id"] == "b"
    assert scores["b"] > scores["a"]


def test_judge_custom_weights(monkeypatch):
    monkeypatch.setenv("RAEBURN_SCORE_WEIGHTS", "0.1,0.1,0.7,0.1")
    candidates = [
        {"id": "a", "content": "short keyword", "model": "m1", "latency": 10, "error": None},
        {"id": "b", "content": "This answer is long but slow keyword", "model": "m2", "latency": 2000, "error": None},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "keyword"))
    assert best["id"] == "a"


def test_judge_embedding_backend(monkeypatch):
    class FakeModel:
        def encode(self, s, convert_to_tensor=True):
            return [1.0] if "good" in s else [0.0]

    monkeypatch.setenv("RAEBURN_SCORING_BACKEND", "embedding")
    monkeypatch.setattr("core.scoring.SentenceTransformer", lambda name: FakeModel())
    monkeypatch.setattr("core.scoring.util", type("U", (), {"cos_sim": lambda a, b: [[a[0] * b[0]]]})())
    candidates = [
        {"id": "a", "content": "bad answer", "model": "m1", "latency": 10, "error": None},
        {"id": "b", "content": "good answer", "model": "m2", "latency": 10, "error": None},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "good"))
    assert best["id"] == "b"


def test_judge_model_backend(monkeypatch):
    async def fake_route(prompt: str, agent: dict, session_id: str) -> list[dict]:
        if "good" in prompt:
            return [{"id": "s", "content": "0.9", "model": "judge"}]
        return [{"id": "s", "content": "0.1", "model": "judge"}]

    monkeypatch.setenv("RAEBURN_SCORING_BACKEND", "model")
    monkeypatch.setattr("core.scoring.route_prompt", fake_route)

    candidates = [
        {"id": "a", "content": "bad answer", "model": "m1", "latency": 10, "error": None},
        {"id": "b", "content": "good answer", "model": "m2", "latency": 10, "error": None},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "good"))
    assert best["id"] == "b"


def test_judge_plugin(monkeypatch):
    monkeypatch.setenv("RAEBURN_SCORING_PLUGIN", "tests.scoring_plugin.plugin_score")
    candidates = [
        {"id": "a", "content": "bad answer", "model": "m1", "latency": 10},
        {"id": "b", "content": "good answer", "model": "m2", "latency": 10},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "question"))
    assert best["id"] == "b"


def test_judge_feedback(monkeypatch):
    monkeypatch.setenv("RAEBURN_FEEDBACK_WEIGHT", "1.0")
    candidates = [
        {"id": "a", "content": "bad", "model": "m1", "latency": 10, "feedback": 1.0},
        {"id": "b", "content": "good", "model": "m2", "latency": 10},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "hi"))
    assert best["id"] == "a"


def test_model_judge(monkeypatch):
    async def fake_route(prompt: str, agent: dict, session_id: str, **kwargs):
        return [{"id": "j", "content": "2", "model": "judge"}]

    monkeypatch.setattr("core.judge.route_prompt", fake_route)
    monkeypatch.setenv("RAEBURN_JUDGE_BACKEND", "model")
    candidates = [
        {"id": "a", "content": "first", "model": "m1", "latency": 10},
        {"id": "b", "content": "second", "model": "m2", "latency": 10},
    ]
    best, _ = asyncio.run(judge_outputs(candidates, "question"))
    assert best["id"] == "b"

