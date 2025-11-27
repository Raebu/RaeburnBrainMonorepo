"""Command line interface for :mod:`raeburnmemory`.

This module uses `Typer` to expose commands for adding interactions,
exporting the graph and querying similar prompts.
"""

import json
import os
from typing import Optional
import typer

from .memory_graph import MemoryGraph, DummyModel

app = typer.Typer(add_completion=False, help="Manage the Raeburn memory graph")


def _open_graph(db: str) -> MemoryGraph:
    return MemoryGraph(db_path=db, embedding_model=None)


@app.callback()
def main(
    ctx: typer.Context,
    db: str = typer.Option("~/.raeburnbrain/graph.json", help="Path to graph database"),
) -> None:
    """RaeburnMemory command line interface."""
    ctx.obj = {"db": os.path.expanduser(db)}


@app.command()
def add(
    ctx: typer.Context,
    prompt_id: str = typer.Option(..., help="Prompt identifier"),
    prompt_text: str = typer.Option(..., help="Prompt text"),
    response_id: str = typer.Option(..., help="Response identifier"),
    response_text: str = typer.Option(..., help="Response text"),
    agent_id: str = typer.Option(..., help="Agent identifier"),
    agent_name: str = typer.Option(..., help="Agent name"),
    session_id: str = typer.Option(..., help="Session identifier"),
) -> None:
    """Add a prompt/response interaction to the graph."""
    mg = _open_graph(ctx.obj["db"])
    if isinstance(mg.model, DummyModel):
        typer.echo(
            "Warning: embedding model unavailable; using dummy embeddings", err=True
        )
    mg.add_interaction(
        prompt={"id": prompt_id, "text": prompt_text},
        response={"id": response_id, "text": response_text},
        agent={"id": agent_id, "name": agent_name},
        session_id=session_id,
    )
    mg.export()
    mg.close()


@app.command()
def export(
    ctx: typer.Context, output: Optional[str] = typer.Option(None, help="Output file")
) -> None:
    """Export the graph as JSON."""
    db = ctx.obj["db"]
    if not os.path.exists(db):
        typer.echo(f"Graph file not found: {db}", err=True)
        raise typer.Exit(code=1)
    mg = _open_graph(db)
    data = mg.export(path=output)
    mg.close()
    if output is None:
        typer.echo(json.dumps(data, indent=2))


@app.command()
def similar(
    ctx: typer.Context,
    text: str = typer.Option(..., help="Query text"),
    top_k: int = typer.Option(5, help="Number of results"),
) -> None:
    """Query for prompts with similar embeddings."""
    db = ctx.obj["db"]
    if not os.path.exists(db):
        typer.echo(f"Graph file not found: {db}", err=True)
        raise typer.Exit(code=1)
    mg = _open_graph(db)
    if mg.vector_index.ntotal == 0:
        typer.echo("No embeddings available in graph", err=True)
        raise typer.Exit(code=1)
    if isinstance(mg.model, DummyModel):
        typer.echo("Embeddings model unavailable", err=True)
        raise typer.Exit(code=1)
    ids = mg.get_similar_prompts(text, top_k=top_k)
    for i in ids:
        typer.echo(i)
    mg.close()


if __name__ == "__main__":  # pragma: no cover
    app()
