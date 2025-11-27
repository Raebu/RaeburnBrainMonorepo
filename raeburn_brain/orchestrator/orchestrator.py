from core.router import route_prompt, record_quality
from core.memory_injector import inject_memories
from core.memory_store import MemoryStore
from core.memory_record import MemoryRecord
from agents.identity_engine import get_agent_by_role
from agents.decision_engine import build_prompt
from core.judge import judge_outputs
from utils.logging import log_event
from utils.uuidgen import gen_session_id
from utils.tracing import tracer, async_span
from .task import Task
from datetime import datetime
import time
import os
import asyncio


async def run_orchestration_pipeline(task: Task | dict) -> dict:
    """Orchestrates one complete task cycle."""
    if isinstance(task, dict):
        task = Task(**task)

    session_id = gen_session_id()
    start = time.monotonic()
    user_input = task.user_input
    role = task.agent_role
    priority = task.priority

    async with async_span(
        "orchestration", tracer, attributes={"agent_role": role, "priority": priority}
    ):

        mode = os.getenv("RAEBURN_ORCHESTRATOR_MODE", "prod")
        env_parallel = os.getenv("RAEBURN_ORCHESTRATOR_PARALLEL", "0").lower() in ("1", "true", "yes")
        parallel = env_parallel or priority > 1

        agent = get_agent_by_role(role)
        injected_context = await inject_memories(user_input, agent)
        prompt = build_prompt(agent, user_input, injected_context)

        try:
            async with async_span(
                "route_prompt", tracer, attributes={"parallel": parallel, "priority": priority}
            ):
                candidates = await route_prompt(
                    prompt,
                    agent=agent,
                    session_id=session_id,
                    parallel=parallel,
                    priority=priority,
                )
            best, scores = await judge_outputs(candidates, user_input)
        except Exception as exc:  # noqa: BLE001
            await log_event("orchestration_error", {"session_id": session_id, "error": str(exc)})
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        memory = MemoryRecord(
            input=user_input,
            output=best["content"],
            agent=agent["name"],
            timestamp=datetime.utcnow().isoformat(),
            score=scores.get(best["id"], 1.0),
            session=session_id,
            mode=mode,
            model_used=best["model"],
            duration_ms=duration_ms,
            priority=priority,
        )
        if mode != "dry-run":
            await MemoryStore().save_memory(memory)

        await record_quality(best["model"], scores[best["id"]], session_id)
        if mode != "test":
            await log_event("orchestration_complete", memory.model_dump())

        return {
            "result": best["content"],
            "model_used": best["model"],
            "score": scores[best["id"]],
            "agent": agent["name"],
            "session_id": session_id,
            "mode": mode,
            "duration_ms": duration_ms,
            "priority": priority,
        }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", type=str)
    parser.add_argument("--agent", type=str, default="generalist")
    args = parser.parse_args()
    task = Task(user_input=args.prompt, agent_role=args.agent)
    output = asyncio.run(run_orchestration_pipeline(task))
    print(output["result"])


if __name__ == "__main__":
    main()
