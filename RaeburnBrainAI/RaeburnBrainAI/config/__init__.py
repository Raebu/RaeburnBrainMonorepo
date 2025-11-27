"""Configuration loaders for RaeburnBrainAI.

This module centralizes file/system overrides so the rest of the codebase can
depend on a stable API:
    load_model_registry() -> dict of model configs
    load_installed_models() -> dict of installed model metadata
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

# ``parents[3]`` resolves to the monorepo root: RaeburnMonorepo/
DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_DIR = DEFAULT_ROOT / "config"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _config_dir() -> Path:
    env_path = os.getenv("RAEBURN_CONFIG_DIR")
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_DIR


def load_model_registry() -> Dict[str, Any]:
    """Return the model registry JSON (provider definitions + meta)."""
    return _load_json(_config_dir() / "model_registry.json")


def load_installed_models() -> Dict[str, Any]:
    """Return installed model metadata."""
    return _load_json(_config_dir() / "models_installed.json")


__all__ = [
    "load_model_registry",
    "load_installed_models",
]
