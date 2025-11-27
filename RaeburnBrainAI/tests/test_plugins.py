import json
from raeburn_brain.plugins import PluginManager


def test_plugin_discovery_and_reload(tmp_path):
    plugin_file = tmp_path / "raeburn_test.py"
    plugin_file.write_text("def greet():\n    return 'hi'\n")
    (tmp_path / "meta.json").write_text(json.dumps({"priority": 1}))

    mgr = PluginManager(str(tmp_path))
    assert "raeburn_test" in mgr.plugins
    assert mgr.plugins["raeburn_test"].module.greet() == "hi"
    assert mgr.plugins["raeburn_test"].meta["priority"] == 1

    # modify plugin and reload
    plugin_file.write_text("def greet():\n    return 'bye'\n")
    mgr.reload()
    assert mgr.plugins["raeburn_test"].module.greet() == "bye"


def test_plugin_sandboxing(tmp_path):
    plugin_file = tmp_path / "raeburn_bad.py"
    plugin_file.write_text(
        "registered = False\n" "def register(pm):\n    global registered\n    registered = True\n"
    )
    (tmp_path / "meta.json").write_text(json.dumps({"sandbox": True}))

    mgr = PluginManager(str(tmp_path))
    assert "raeburn_bad" in mgr.plugins
    plg = mgr.plugins["raeburn_bad"]
    assert plg.sandboxed is True
    assert plg.module.registered is False

