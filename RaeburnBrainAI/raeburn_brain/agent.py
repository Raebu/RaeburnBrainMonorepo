from __future__ import annotations

"""Agent lifecycle management for Raeburn Brain AI."""

from dataclasses import dataclass, asdict
from typing import Iterable, List

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from .db import Base, SessionLocal


# --- Persona generation ----------------------------------------------------

def generate_persona(traits: Iterable[str]) -> str:
    """Return a simple persona description based on given traits."""
    return "Persona: " + ", ".join(traits)


# --- Agent and registry ----------------------------------------------------

@dataclass
class Agent:
    """Represents a single agent and its performance metrics."""

    id: str
    persona: str
    title: str = "novice"
    score: float = 0.0
    trials: int = 0
    successes: int = 0
    sandboxed: bool = False
    mentor_id: str | None = None

    def record_result(self, success: bool) -> None:
        """Update performance statistics and lifecycle state."""
        self.trials += 1
        if success:
            self.successes += 1
        self.score = self.successes / self.trials
        self._update_status()

    # internal helpers -----------------------------------------------------
    def _update_status(self) -> None:
        if self.trials < 5:
            return
        if self.score >= 0.8:
            self.title = "promoted"
            self.sandboxed = False
        elif self.score <= 0.2:
            self.title = "sandboxed"
            self.sandboxed = True
        elif self.score <= 0.5:
            self.title = "demoted"
            self.sandboxed = False


class AgentModel(Base):
    """SQLAlchemy table representing agents."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    persona: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, default="novice")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    trials: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)
    sandboxed: Mapped[bool] = mapped_column(Boolean, default=False)
    mentor_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"))


def _to_agent(model: AgentModel) -> Agent:
    return Agent(
        id=model.id,
        persona=model.persona,
        title=model.title,
        score=model.score,
        trials=model.trials,
        successes=model.successes,
        sandboxed=model.sandboxed,
        mentor_id=model.mentor_id,
    )


class AgentRegistry:
    """Persist agents and expose lookup/update helpers."""

    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self.session_factory = session_factory or SessionLocal

    def list(self) -> List[Agent]:
        with self.session_factory() as sess:
            models = sess.query(AgentModel).all()
            return [_to_agent(m) for m in models]

    def get(self, agent_id: str) -> Agent:
        with self.session_factory() as sess:
            model = sess.get(AgentModel, agent_id)
            if not model:
                raise KeyError(agent_id)
            return _to_agent(model)

    def ensure(self, agent_id: str, traits: Iterable[str]) -> Agent:
        with self.session_factory() as sess:
            model = sess.get(AgentModel, agent_id)
            if not model:
                persona = generate_persona(traits)
                model = AgentModel(id=agent_id, persona=persona)
                sess.add(model)
                sess.commit()
                sess.refresh(model)
            return _to_agent(model)

    def record(self, agent_id: str, success: bool) -> None:
        with self.session_factory() as sess:
            model = sess.get(AgentModel, agent_id)
            if not model:
                raise KeyError(agent_id)
            agent = _to_agent(model)
            agent.record_result(success)
            for k, v in asdict(agent).items():
                if k != "id":
                    setattr(model, k, v)
            sess.commit()

    def mentor(self, agent_id: str, mentor_id: str) -> None:
        with self.session_factory() as sess:
            agent = sess.get(AgentModel, agent_id)
            mentor = sess.get(AgentModel, mentor_id)
            if not agent or not mentor:
                raise KeyError("agent or mentor not found")
            agent.mentor_id = mentor_id
            sess.commit()

    def clone(self, agent_id: str, new_id: str) -> Agent:
        with self.session_factory() as sess:
            src = sess.get(AgentModel, agent_id)
            if not src:
                raise KeyError(agent_id)
            clone = AgentModel(
                id=new_id,
                persona=src.persona,
                title=src.title,
                score=src.score,
                trials=src.trials,
                successes=src.successes,
                sandboxed=src.sandboxed,
                mentor_id=src.id,
            )
            sess.add(clone)
            sess.commit()
            return _to_agent(clone)


__all__ = [
    "Agent",
    "AgentModel",
    "AgentRegistry",
    "generate_persona",
]
