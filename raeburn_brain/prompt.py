from __future__ import annotations

"""Prompt management utilities using Jinja2 templates."""

from dataclasses import dataclass, field
from typing import Dict, List, Iterable, Tuple, Any, Iterator

from jinja2 import Environment, FileSystemLoader, meta

from .core import MemoryStore


@dataclass
class PromptManager:
    """Render prompts with optional memory and chat history."""

    templates_dir: str = "agent_templates"
    store: MemoryStore | None = None
    history: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.env = Environment(loader=FileSystemLoader(self.templates_dir))

    def _validate(self, template_name: str, variables: Iterable[str]) -> None:
        """Ensure all variables required by the template are present."""
        source, *_ = self.env.loader.get_source(self.env, template_name)
        required = meta.find_undeclared_variables(self.env.parse(source))
        missing = set(required) - set(variables)
        if missing:
            raise ValueError(f"Missing variables for template {template_name}: {', '.join(sorted(missing))}")

    def add_history(self, agent_id: str, message: str) -> None:
        """Append a message to the agent's chat history."""
        msgs = self.history.setdefault(agent_id, [])
        msgs.append(message)
        self.history[agent_id] = msgs[-10:]  # keep last 10

    def render(
        self,
        agent_id: str,
        template_name: str,
        *,
        mood: str = "neutral",
        tone: str = "neutral",
        debug: bool = False,
        **data: Any,
    ) -> str | Tuple[str, Dict[str, Any]]:
        """Render ``template_name`` with memory, history, and modifiers.

        If ``debug`` is True, return a tuple of (output, trace).
        """
        template = self.env.get_template(template_name)
        history = "\n".join(self.history.get(agent_id, []))
        context = ""
        if self.store:
            context = "\n".join(m.text for m in self.store.get(agent_id))
        variables = {
            "mood": mood,
            "tone": tone,
            "history": history,
            "context": context,
            **data,
        }
        self._validate(template_name, variables.keys())
        output = template.render(**variables)
        if debug:
            return output, {"template": template_name, "variables": variables, "output": output}
        return output

    def render_stream(
        self,
        agent_id: str,
        template_name: str,
        *,
        mood: str = "neutral",
        tone: str = "neutral",
        **data: Any,
    ) -> Iterator[str]:
        """Stream ``template_name`` chunks as they are rendered."""
        template = self.env.get_template(template_name)
        history = "\n".join(self.history.get(agent_id, []))
        context = ""
        if self.store:
            context = "\n".join(m.text for m in self.store.get(agent_id))
        variables = {
            "mood": mood,
            "tone": tone,
            "history": history,
            "context": context,
            **data,
        }
        self._validate(template_name, variables.keys())
        for chunk in template.generate(**variables):
            yield chunk

    def run_pipeline(
        self,
        agent_id: str,
        pipeline: Iterable[str],
        *,
        mood: str = "neutral",
        tone: str = "neutral",
        debug: bool = False,
        **data: Any,
    ) -> str | Tuple[str, List[Dict[str, Any]]]:
        """Execute a sequence of templates as a pipeline.

        Each step receives ``previous_output`` from the prior template. If
        ``debug`` is True, a list of trace dictionaries is returned.
        """
        traces: List[Dict[str, Any]] = []
        previous_output = data.get("previous_output", "")
        for name in pipeline:
            result, trace = self.render(
                agent_id,
                name,
                mood=mood,
                tone=tone,
                debug=True,
                previous_output=previous_output,
                **data,
            )
            previous_output = result
            traces.append(trace)
        if debug:
            return previous_output, traces
        return previous_output


__all__ = ["PromptManager"]
