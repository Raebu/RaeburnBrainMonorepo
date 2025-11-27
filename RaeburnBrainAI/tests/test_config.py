import pytest

from raeburn_brain.config import Settings


def test_settings_env_loading(monkeypatch):
    monkeypatch.setenv("RAEBURN_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("RAEBURN_LOG_LEVEL", "DEBUG")
    s = Settings()
    assert s.database_url == "sqlite:///test.db"
    assert s.log_level == "DEBUG"


def test_settings_env_file(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("RAEBURN_DATABASE_URL=sqlite:///file.db\nRAEBURN_LOG_LEVEL=WARNING")
    monkeypatch.setenv("RAEBURN_CONFIG_FILE", str(env))
    s = Settings.load()
    assert s.database_url == "sqlite:///file.db"
    assert s.log_level == "WARNING"


def test_invalid_log_level(monkeypatch):
    monkeypatch.setenv("RAEBURN_LOG_LEVEL", "INVALID")
    with pytest.raises(Exception):
        Settings()


def test_config_signature(monkeypatch):
    secret = "sekret"
    s = Settings()
    import hashlib
    import hmac
    sig = hmac.new(secret.encode(), s.model_dump_json().encode(), hashlib.sha256).hexdigest()
    monkeypatch.setenv("RAEBURN_CONFIG_SECRET", secret)
    monkeypatch.setenv("RAEBURN_CONFIG_SIGNATURE", sig)
    import importlib
    import raeburn_brain.config as config
    importlib.reload(config)


def test_config_signature_fail(monkeypatch):
    monkeypatch.setenv("RAEBURN_CONFIG_SECRET", "x")
    monkeypatch.setenv("RAEBURN_CONFIG_SIGNATURE", "bad")
    import importlib
    import raeburn_brain.config as config
    with pytest.raises(SystemExit):
        importlib.reload(config)

