"""The production build preflight refuses unsafe reuse and unpinned tooling."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
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


VENDORED = "msvcp140-" + "0" * 32 + ".dll"


def synthetic_pe(*dll_names: str, delayed: tuple[str, ...] = ()) -> bytes:
    """PE32+ image with one section holding ordinary and delay-load imports."""
    optional, section_rva, raw = 0x40 + 24, 0x1000, 0x400
    image = bytearray(raw)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x40)
    image[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HH", image, 0x44, 0x8664, 1)
    struct.pack_into("<H", image, 0x40 + 20, 240)
    struct.pack_into("<H", image, optional, 0x20B)
    struct.pack_into("<I", image, optional + 108, 16)
    descriptors = 20 * (len(dll_names) + 1)
    delay_descriptors = 32 * (len(delayed) + 1)
    struct.pack_into("<II", image, optional + 112 + 8, section_rva, descriptors)
    if delayed:
        struct.pack_into(
            "<II",
            image,
            optional + 112 + 8 * 13,
            section_rva + descriptors,
            delay_descriptors,
        )
    body = bytearray(descriptors + delay_descriptors)
    for index, name in enumerate(dll_names):
        struct.pack_into("<I", body, 20 * index + 12, section_rva + len(body))
        body += name.encode() + b"\0"
    for index, name in enumerate(delayed):
        at = descriptors + 32 * index
        struct.pack_into("<II", body, at, 1, section_rva + len(body))
        body += name.encode() + b"\0"
    section = optional + 240
    struct.pack_into(
        "<8sIIII", image, section, b".idata", len(body), section_rva, len(body), raw
    )
    return bytes(image + body)


def test_import_names_reads_the_pe_import_directory() -> None:
    build = load()
    names = [name for _, name in build.import_names(synthetic_pe("A.dll", VENDORED))]
    assert names == ["A.dll", VENDORED]
    with pytest.raises(ValueError, match="PE"):
        build.import_names(b"synthetic, not an executable" * 4)


def test_vendored_runtime_imports_are_relinked_with_a_receipt(tmp_path: Path) -> None:
    build = load()
    library = tmp_path / "numpy" / "_core.pyd"
    library.parent.mkdir()
    library.write_bytes(synthetic_pe("python313.dll", VENDORED))
    (tmp_path / "plain.dll").write_bytes(synthetic_pe("kernel32.dll"))
    receipts = build.relink_vendored_runtime(tmp_path)
    assert [item["path"] for item in receipts] == ["numpy/_core.pyd"]
    assert receipts[0]["replaced_imports"] == VENDORED
    names = [name for _, name in build.import_names(library.read_bytes())]
    assert names == ["python313.dll", "msvcp140.dll"]
    assert len(library.read_bytes()) == len(synthetic_pe("python313.dll", VENDORED))
    build.verify_no_microsoft_runtime(tmp_path)


@pytest.mark.parametrize(
    "name", ["vcruntime140.dll", "VCRUNTIME140_1.dll", "msvcp140_2.dll", VENDORED]
)
def test_bundled_microsoft_runtime_files_are_refused(tmp_path: Path, name: str) -> None:
    build = load()
    (tmp_path / name).write_bytes(synthetic_pe("kernel32.dll"))
    with pytest.raises(ValueError, match="Microsoft"):
        build.verify_no_microsoft_runtime(tmp_path)


@pytest.mark.parametrize("delay", [False, True])
def test_an_unrelinked_vendored_import_is_refused(tmp_path: Path, delay: bool) -> None:
    build = load()
    image = (
        synthetic_pe("kernel32.dll", delayed=(VENDORED,))
        if delay
        else synthetic_pe(VENDORED)
    )
    (tmp_path / "numpy.pyd").write_bytes(image)
    with pytest.raises(ValueError, match="vendored"):
        build.verify_no_microsoft_runtime(tmp_path)


def test_delay_loaded_vendored_imports_are_relinked_too(tmp_path: Path) -> None:
    build = load()
    library = tmp_path / "numpy.pyd"
    library.write_bytes(synthetic_pe("kernel32.dll", delayed=(VENDORED,)))
    receipts = build.relink_vendored_runtime(tmp_path)
    assert receipts[0]["replaced_imports"] == VENDORED
    names = [name for _, name in build.import_names(library.read_bytes())]
    assert names == ["kernel32.dll", "msvcp140.dll"]
    build.verify_no_microsoft_runtime(tmp_path)


def test_build_interpreter_must_match_the_pinned_runtime(tmp_path: Path) -> None:
    build = load()
    (tmp_path / "python313.dll").write_bytes(b"synthetic runtime")
    manifest = {
        "files": {
            "python313.dll": hashlib.sha256(b"synthetic runtime").hexdigest(),
            "DLLs/_ssl.pyd": hashlib.sha256(b"absent").hexdigest(),
        }
    }
    assert build.runtime_mismatches(tmp_path, manifest) == ["DLLs/_ssl.pyd"]
    (tmp_path / "DLLs").mkdir()
    (tmp_path / "DLLs" / "_ssl.pyd").write_bytes(b"absent")
    assert build.runtime_mismatches(tmp_path, manifest) == []


def test_runtime_manifest_pins_the_official_python_release() -> None:
    manifest = json.loads(
        (Path(__file__).parents[2] / "distribution/python-runtime.json").read_text()
    )
    assert manifest["producer"] == "Python Software Foundation"
    assert manifest["build"].startswith("tags/v" + manifest["version"])
    assert "python313.dll" in manifest["files"]
    assert not any(name.lower().startswith("vcruntime") for name in manifest["files"])


def test_truststore_must_be_the_reviewed_wheel_and_is_license_audited() -> None:
    build = load()
    project = Path(__file__).parents[2]
    assert build.installed_mismatches("truststore", build.TRUSTSTORE_FILES) == []
    altered = dict(build.TRUSTSTORE_FILES, **{"truststore/_api.py": "0" * 64})
    assert build.installed_mismatches("truststore", altered) == ["truststore/_api.py"]
    pins = (project / "tools/m10/requirements-build.txt").read_text().splitlines()
    assert "truststore==0.10.4" in pins
    register = json.loads(
        (project / "distribution/component-register.json").read_text()
    )
    (entry,) = [c for c in register["components"] if c["name"] == "truststore"]
    assert (entry["version"], entry["selected_license"]) == ("0.10.4", "MIT")


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
