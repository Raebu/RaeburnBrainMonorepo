"""Plugin management for Raeburn Brain AI."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Dict


@dataclass
class Plugin:
    """Loaded plugin information."""

    name: str
    module: ModuleType
    meta: dict
    sandboxed: bool = False


class PluginManager:
    """Discover and hot-reload plugins from a directory."""

    def __init__(self, path: str | Path = "plugins", watch: bool = False, interval: float = 1.0) -> None:
        self.path = Path(path)
        self.interval = interval
        self.plugins: Dict[str, Plugin] = {}
        self._mtimes: Dict[str, float] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.discover()
        if watch:
            self.watch()

    def discover(self) -> None:
        """Load all plugins found in ``self.path``."""
        for file in self.path.glob("raeburn_*.py"):
            self._load(file)

    def _load(self, file: Path) -> None:
        name = file.stem
        mtime = file.stat().st_mtime
        if self._mtimes.get(name) == mtime:
            return
        spec = importlib.util.spec_from_file_location(name, file)
        if not spec or not spec.loader:
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        meta_path = file.with_name("meta.json")
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                meta = {}
        sandboxed = bool(meta.get("sandbox") or meta.get("sandboxed"))
        plugin = Plugin(name, module, meta, sandboxed)
        if not sandboxed and hasattr(module, "register"):
            try:
                module.register(self)
            except Exception:
                plugin.sandboxed = True
        self.plugins[name] = plugin
        self._mtimes[name] = mtime

    def reload(self) -> None:
        """Reload all plugins regardless of modification time."""
        self.plugins.clear()
        self._mtimes.clear()
        self.discover()

    def watch(self) -> None:
        """Start a background thread for hot-reloading."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._stop.set()
            self._thread.join()
            self._thread = None
            self._stop.clear()

    # internal -------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            self.discover()
            time.sleep(self.interval)


__all__ = ["Plugin", "PluginManager"]
