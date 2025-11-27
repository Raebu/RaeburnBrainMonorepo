import os
import sys
import subprocess


def test_cli_runs(tmp_path):
    env = os.environ.copy()
    env["RAEBURN_ORCHESTRATOR_MODE"] = "test"
    env["RAEBURN_MEMORY_PATH"] = str(tmp_path / "mem.log")
    env["RAEBURN_LOG_PATH"] = str(tmp_path)
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("HF_API_TOKEN", None)

    result = subprocess.run(
        [sys.executable, "-m", "raeburn_brain.orchestrator.orchestrator", "hi"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout.strip()
    assert (tmp_path / "mem.log").exists()
