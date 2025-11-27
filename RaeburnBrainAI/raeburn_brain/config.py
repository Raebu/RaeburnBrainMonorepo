from __future__ import annotations

"""Configuration management for Raeburn Brain AI."""

import os
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RAEBURN_",
    )

    debug: bool = Field(False, description="Enable debug mode")
    database_url: str = Field(
        "sqlite:///raeburn.db", description="Database connection URL"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Logging verbosity"
    )

    @classmethod
    def load(cls) -> "Settings":
        """Load settings using optional env file from ``RAEBURN_CONFIG_FILE``."""
        env_file = os.getenv("RAEBURN_CONFIG_FILE")
        kwargs = {"_env_file": env_file} if env_file else {}
        return cls(**kwargs)


try:
    settings = Settings.load()
except ValidationError as exc:  # pragma: no cover - fail hard on import
    raise SystemExit(f"Invalid configuration: {exc}")

# Optional configuration signature verification
secret = os.getenv("RAEBURN_CONFIG_SECRET")
signature = os.getenv("RAEBURN_CONFIG_SIGNATURE")
if secret and signature:
    import hashlib
    import hmac

    computed = hmac.new(
        secret.encode(), settings.model_dump_json().encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, computed):
        raise SystemExit("Invalid configuration signature")

__all__ = ["Settings", "settings"]
