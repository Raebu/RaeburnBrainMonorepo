import importlib
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires(*modules): skip if required modules are missing",
    )


def pytest_runtest_setup(item):
    marker = item.get_closest_marker("requires")
    if marker:
        missing = []
        for mod in marker.args:
            try:
                importlib.import_module(mod)
            except ImportError:
                missing.append(mod)
        if missing:
            pytest.skip("Missing required modules: " + ", ".join(missing))
