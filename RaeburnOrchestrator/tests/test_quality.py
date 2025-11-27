import json
import sqlite3

import pytest

from core.router import record_quality


@pytest.mark.asyncio
async def test_record_quality_writes_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path / "qlogs"))
    await record_quality("model-x", 0.42, "sess_test")
    qlog = tmp_path / "qlogs" / "quality.log"
    assert qlog.exists()
    data = json.loads(qlog.read_text().strip())
    assert data["model"] == "model-x"
    assert data["score"] == 0.42
    assert data["session"] == "sess_test"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_record_quality_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "logs.db"
    monkeypatch.setenv("RAEBURN_DB_PATH", str(db))
    await record_quality("model-y", 0.1, "sess")
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT json FROM quality_logs").fetchone()[0]
    conn.close()
    rec = json.loads(row)
    assert rec["model"] == "model-y"


@pytest.mark.asyncio
async def test_quality_log_rotation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path))
    monkeypatch.setenv("RAEBURN_LOG_MAX_BYTES", "1")
    await record_quality("a", 0.1, "s1")
    await record_quality("b", 0.2, "s2")
    files = list(tmp_path.glob("quality.log*"))
    assert len(files) >= 2


@pytest.mark.asyncio
async def test_record_quality_otel(monkeypatch):
    class Hist:
        def __init__(self) -> None:
            self.records: list[tuple[float, dict[str, str]]] = []

        def record(self, value: float, attributes: dict[str, str] | None = None) -> None:
            self.records.append((value, attributes or {}))

    h = Hist()
    monkeypatch.setattr("core.router.OTEL_QUALITY_HIST", h)
    await record_quality("model-z", 0.33, "sid")
    assert h.records and h.records[0][0] == 0.33
    assert h.records[0][1]["model"] == "model-z"
