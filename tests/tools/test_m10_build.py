"""The production build preflight refuses unsafe reuse and unpinned tooling."""

from __future__ import annotations

import importlib.util
import subprocess
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


@pytest.mark.parametrize("dirty", ["tracked", "untracked"])
def test_build_refuses_source_not_identified_by_head(
    tmp_path: Path, dirty: str
) -> None:
    build = load()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "example.py"
    source.write_text("# synthetic build input\n")
    subprocess.run(["git", "add", "src"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=STI Development",
            "-c",
            "user.email=dev@example.invalid",
            "commit",
            "-qm",
            "synthetic input",
        ],
        cwd=tmp_path,
        check=True,
    )
    revision = build.source_revision(tmp_path)
    assert len(revision) == 40
    (tmp_path / "governance.md").write_text("pending local docs\n")
    assert build.source_revision(tmp_path) == revision
    if dirty == "tracked":
        source.write_text("# modified synthetic input\n")
    else:
        (tmp_path / "src" / "extra.py").write_text("# new synthetic input\n")
    with pytest.raises(ValueError, match="committed"):
        build.source_revision(tmp_path)


def test_an_overlong_new_build_root_is_rejected_before_creation(tmp_path: Path) -> None:
    build = load()
    output = tmp_path / ("synthetic-output-" * 8)
    with pytest.raises(ValueError, match="short"):
        build.prepare_output(output)
    assert not output.exists()


def test_build_environment_excludes_ambient_native_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    build = load()
    system = tmp_path / "synthetic-windows"
    monkeypatch.setenv("SYSTEMROOT", str(system))
    monkeypatch.setenv("PATH", "synthetic-unrelated-native-tools")
    monkeypatch.setenv("QT_PLUGIN_PATH", "synthetic-external-qt")
    environment = build.build_environment(tmp_path / "output")
    assert "synthetic-unrelated-native-tools" not in environment["PATH"]
    assert str(system / "System32") in environment["PATH"].split(os.pathsep)
    assert "QT_PLUGIN_PATH" not in environment
    assert environment["HF_HOME"] == str(tmp_path / "output" / "build-hub-cache")
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
