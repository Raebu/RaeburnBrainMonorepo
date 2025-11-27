
"""Prompt construction helpers."""

from __future__ import annotations

from typing import Iterable


def build_prompt(agent: dict, user_input: str, context: Iterable[str]) -> str:
    """Return a prompt combining system message, user input and context."""
    context_str = "\n".join(context)
    parts: list[str] = []
    system = agent.get("system_prompt")
    if system:
        parts.append(system)

    parts.append(f"User: {user_input}")

    extras: list[str] = []
    if context_str:
        extras.append("Context:\n" + context_str)

    style = agent.get("prompt_style")
    if style:
        extras.append("Style: " + style)

    if extras:
        parts.append("\n".join(extras))

    return "\n\n".join(parts)

