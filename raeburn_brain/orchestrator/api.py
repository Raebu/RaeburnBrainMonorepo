from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .orchestrator import run_orchestration_pipeline
from .task import Task

app = FastAPI(title="Raeburn Orchestrator API")


class TaskIn(BaseModel):
    user_input: str
    agent_role: str | None = None
    priority: int | None = None


@app.post("/orchestrate")
async def orchestrate(task: TaskIn):
    try:
        result = await run_orchestration_pipeline(
            Task(
                user_input=task.user_input,
                agent_role=task.agent_role or "generalist",
                priority=task.priority or 1,
            )
        )
        return result
    except Exception as exc:  # pragma: no cover - pass through
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
