import json
import pytest
from utils.uuidgen import gen_session_id
from utils.logging import log_event


def test_gen_session_id_format():
    sid = gen_session_id()
    assert sid.startswith("sess_")
    assert len(sid) == 13


@pytest.mark.asyncio
async def test_log_event_writes_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path / "mylogs"))
    await log_event("test-event", {"foo": "bar"})
    log_file = tmp_path / "mylogs" / "orchestrator.log"
    assert log_file.exists()
    data = json.loads(log_file.read_text().strip())
    assert data["event"] == "test-event"
    assert data["foo"] == "bar"


@pytest.mark.asyncio
async def test_log_event_failure(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("aiofiles.open", boom)
    with pytest.raises(OSError):
        await log_event("err", {})


@pytest.mark.asyncio
async def test_log_event_sqlite(tmp_path, monkeypatch):
    db = tmp_path / "logs.db"
    monkeypatch.setenv("RAEBURN_DB_PATH", str(db))
    await log_event("db-event", {"a": 1})
    import sqlite3
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT json FROM logs").fetchone()[0]
    conn.close()
    data = json.loads(row)
    assert data["event"] == "db-event"


@pytest.mark.asyncio
async def test_log_event_rotation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAEBURN_LOG_PATH", str(tmp_path))
    monkeypatch.setenv("RAEBURN_LOG_MAX_BYTES", "1")
    await log_event("one", {})
    await log_event("two", {})
    files = list(tmp_path.glob("orchestrator.log*"))
    assert len(files) >= 2


@pytest.mark.asyncio
async def test_log_event_otel(monkeypatch):
    class Counter:
        def __init__(self) -> None:
            self.calls: list[tuple[int, dict[str, str]]] = []

        def add(self, value: int, attributes: dict[str, str] | None = None) -> None:
            self.calls.append((value, attributes or {}))

    c = Counter()
    monkeypatch.setattr("utils.logging.OTEL_EVENT_COUNTER", c)
    await log_event("otel", {"x": 1})
    assert c.calls and c.calls[0][0] == 1
    assert c.calls[0][1]["event"] == "otel"
