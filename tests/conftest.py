"""Load integration modules without importing the Home Assistant package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "jooki"


def _load(module_name: str, filename: str):
    """Import a module by path so ``custom_components.jooki`` stays unloaded."""
    path = _PACKAGE / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_models():
    """Import ``models.py`` by path."""
    return _load("jooki_models", "models.py")


def load_device_commands():
    """Import ``device_commands.py`` by path."""
    return _load("jooki_device_commands", "device_commands.py")


def load_device_config():
    """Import ``device_config.py`` by path."""
    return _load("jooki_device_config", "device_config.py")


def load_identity():
    """Import ``identity.py`` by path."""
    return _load("jooki_identity", "identity.py")


@pytest.fixture(scope="session")
def models():
    """Session-wide models module."""
    return load_models()


@pytest.fixture(scope="session")
def device_commands():
    """Session-wide command encoding module."""
    return load_device_commands()


@pytest.fixture(scope="session")
def device_config():
    """Session-wide topic tables."""
    return load_device_config()


@pytest.fixture(scope="session")
def identity():
    """Session-wide hostname identity helpers."""
    return load_identity()
