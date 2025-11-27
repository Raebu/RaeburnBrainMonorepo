import pytest

from raeburn_brain.core import MemoryStore
from raeburn_brain.prompt import PromptManager


def test_prompt_render_with_context(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "hello.txt").write_text(
        "Mood: {{ mood }}\nTone: {{ tone }}\nHistory: {{ history }}\nContext: {{ context }}\nName: {{ name }}"
    )
    store = MemoryStore()
    store.add("a1", "past memory")
    manager = PromptManager(str(templates), store=store)
    manager.add_history("a1", "hi")
    out = manager.render("a1", "hello.txt", mood="happy", tone="formal", name="Bob")
    assert "happy" in out
    assert "formal" in out
    assert "hi" in out
    assert "past memory" in out
    assert "Bob" in out


def test_prompt_missing_var_validation(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.txt").write_text("Hello {{ name }} {{ title }}")
    mgr = PromptManager(str(templates))
    with pytest.raises(ValueError):
        mgr.render("a", "t.txt", name="Alice")


def test_prompt_pipeline_debug(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "step1.txt").write_text("{{ name }}")
    (templates / "step2.txt").write_text("{{ previous_output }} world")
    mgr = PromptManager(str(templates))
    output, traces = mgr.run_pipeline(
        "a",
        ["step1.txt", "step2.txt"],
        name="Hello",
        debug=True,
    )
    assert output == "Hello world"
    assert traces[0]["output"] == "Hello"


def test_render_stream(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.txt").write_text("Hello {{ name }}")
    mgr = PromptManager(str(templates))
    chunks = list(mgr.render_stream("a", "t.txt", name="Bob"))
    assert "Hello Bob" == "".join(chunks)


