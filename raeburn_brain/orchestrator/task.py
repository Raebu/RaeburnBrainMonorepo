from dataclasses import dataclass

@dataclass
class Task:
    """Structured task description passed to the orchestrator."""

    user_input: str
    agent_role: str = "generalist"
    priority: int = 1
