import importlib
from raeburn_brain.db import run_migrations


def test_model_competition(tmp_path, monkeypatch):
    monkeypatch.setenv("RAEBURN_DATABASE_URL", f"sqlite:///{tmp_path}/db.db")
    import raeburn_brain.config as config
    import raeburn_brain.db as db
    import raeburn_brain.agent as agent_mod
    import raeburn_brain.judging as judging_mod
    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(agent_mod)
    importlib.reload(judging_mod)

    run_migrations()
    from raeburn_brain.agent import AgentRegistry
    from raeburn_brain.judging import Judge
    from raeburn_brain.model import BaseModelFetcher

    class DummyFetcher(BaseModelFetcher):
        def __init__(self, name: str, resp: str) -> None:
            super().__init__(name)
            self.resp = resp

        def generate(self, prompt: str) -> str:
            return self.resp

    class JudgeFetcher(BaseModelFetcher):
        def __init__(self) -> None:
            super().__init__("judge")

        def generate(self, prompt: str) -> str:
            data = eval(prompt)
            responses = data["responses"]
            return max(responses, key=lambda k: len(responses[k]))

    registry = AgentRegistry()
    judge = Judge(JudgeFetcher(), registry)

    agents = {
        "a1": DummyFetcher("m1", "short"),
        "a2": DummyFetcher("m2", "the best response"),
        "a3": DummyFetcher("m3", "ok"),
    }
    winner = judge.compete("hi", agents).winner_id
    assert winner == "a2"
    assert registry.get("a2").successes == 1
    assert registry.get("a1").trials == 1

