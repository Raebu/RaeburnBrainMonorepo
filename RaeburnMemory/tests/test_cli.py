import pytest
import numpy as np  # noqa: F401
from typer.testing import CliRunner

from raeburnmemory.cli import app
from raeburnmemory import memory_graph

pytestmark = pytest.mark.requires("numpy")

runner = CliRunner()


def test_cli_add_and_query(tmp_path):
    db = tmp_path / "g.json"
    result = runner.invoke(
        app,
        [
            "--db",
            str(db),
            "add",
            "--prompt-id",
            "p1",
            "--prompt-text",
            "Hello",
            "--response-id",
            "r1",
            "--response-text",
            "Hi",
            "--agent-id",
            "a1",
            "--agent-name",
            "Bot",
            "--session-id",
            "s",
        ],
    )
    assert result.exit_code == 0
    mg = memory_graph.MemoryGraph(db_path=str(db), embedding_model=None)
    ids = mg.get_similar_prompts("Hello")
    assert "p1" in ids


def test_cli_export(tmp_path):
    db = tmp_path / "g.json"
    out = tmp_path / "export.json"
    runner.invoke(
        app,
        [
            "--db",
            str(db),
            "add",
            "--prompt-id",
            "p1",
            "--prompt-text",
            "Hello",
            "--response-id",
            "r1",
            "--response-text",
            "Hi",
            "--agent-id",
            "a1",
            "--agent-name",
            "Bot",
            "--session-id",
            "s",
        ],
    )
    result = runner.invoke(app, ["--db", str(db), "export", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    data = out.read_text()
    assert "p1" in data


def test_cli_missing_db(tmp_path):
    missing = tmp_path / "missing.json"
    result = runner.invoke(app, ["--db", str(missing), "export"])
    assert result.exit_code != 0


def test_cli_no_embeddings(tmp_path):
    db = tmp_path / "g.json"
    runner.invoke(
        app,
        [
            "--db",
            str(db),
            "add",
            "--prompt-id",
            "p1",
            "--prompt-text",
            "Hello",
            "--response-id",
            "r1",
            "--response-text",
            "Hi",
            "--agent-id",
            "a1",
            "--agent-name",
            "Bot",
            "--session-id",
            "s",
        ],
    )
    idx = tmp_path / "g.json.faiss"
    if idx.exists():
        idx.unlink()
    else:
        (tmp_path / "g.json.vectors.npy").unlink()
    result = runner.invoke(app, ["--db", str(db), "similar", "--text", "Hi"])
    assert result.exit_code != 0
