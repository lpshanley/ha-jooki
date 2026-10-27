"""Load models.py without importing the Home Assistant package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODELS_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "jooki" / "models.py"
)


def load_models():
    """Import ``models.py`` by path so ``custom_components.jooki`` stays unloaded."""
    spec = importlib.util.spec_from_file_location("jooki_models", _MODELS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {_MODELS_PATH}")
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def models():
    """Session-wide models module."""
    return load_models()
