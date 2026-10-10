"""The production build preflight refuses unsafe reuse and unpinned tooling."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load() -> ModuleType:
    path = Path(__file__).parents[2] / "tools/m10/build.py"
    spec = importlib.util.spec_from_file_location("m10_build", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_never_reuses_an_existing_output(tmp_path: Path) -> None:
    build = load()
    with pytest.raises(ValueError, match="new"):
        build.prepare_output(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_weight_or_database_in_bundle_is_rejected(tmp_path: Path) -> None:
    build = load()
    (tmp_path / "model.safetensors").write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="forbidden"):
        build.audit_bundle(tmp_path)
