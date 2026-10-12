"""B4 narrows only on recorded licence texts; Intel OpenMP terms stay open."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGAL = ROOT / "distribution" / "legal"
VERSIONS = {"tokenizers": "0.22.2", "safetensors": "0.8.0"}


def load(name: str) -> Any:
    path = ROOT / "tools" / "m10" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"sti_b4_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def index() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (LEGAL / "rust-crates" / "index.json").read_text(encoding="utf-8")
    )
    return data


def evidence() -> dict[str, Any]:
    return dict(
        software_renderer=False,
        microsoft_runtime=False,
        python_runtime_verified=True,
        language_model_bundled=False,
    )


def test_b4_keeps_general_wording_without_a_coverage_check() -> None:
    compliance = load("compliance")
    blockers = compliance.distribution_blockers(
        {"qt_libraries_verified": True}, **evidence()
    )
    assert compliance.B4 in blockers


def test_b4_names_what_remains_and_clears_only_when_nothing_does() -> None:
    compliance = load("compliance")
    narrowed = compliance.distribution_blockers(
        {"qt_libraries_verified": True},
        **evidence(),
        b4_remaining=[compliance.B4_INTEL],
    )
    assert [item[:3] for item in narrowed] == ["B1:", "B4:"]
    assert compliance.B4_INTEL in narrowed[1]
    cleared = compliance.distribution_blockers(
        {"qt_libraries_verified": True}, **evidence(), b4_remaining=[]
    )
    assert [item[:3] for item in cleared] == ["B1:"]


def test_committed_rust_notices_cover_the_pinned_superset() -> None:
    compliance = load("compliance")
    summary, gaps = compliance.rust_notice_coverage(LEGAL, VERSIONS)
    assert gaps == []
    assert summary["complete"] is True
    assert summary["not_linked_on_windows"] == ["r-efi", "wasip2"]
    data = index()
    assert data["without_notice_text"] == []
    crates = {f"{c['name']}@{c['version']}": c for c in data["crates"]}
    # 147 crates.io packages from the tokenizers lock (149 entries less its two
    # workspace packages), the safetensors SBOM additions, and the workspace pair.
    tokenizers = [c for c in data["crates"] if "tokenizers 0.22.2" in c["owners"]]
    assert len([c for c in tokenizers if c["source"] == "crates.io"]) == 147
    assert crates["tokenizers@0.22.2"]["sha256"] is None
    assert crates["tokenizers-python@0.22.2"]["notices"]
    compiled = json.loads(
        (ROOT / "docs/evidence/m10-e1/rust-compiled-crates.json").read_text(
            encoding="utf-8"
        )
    )["binaries"]
    for binary in ("tokenizers.pyd", "_safetensors_rust.pyd"):
        for crate in compiled[binary]["crates"]:
            assert crates[crate]["notices"], crate
            assert crates[crate]["found_in_binary"] is True
    header_notices = [n["path"] for n in crates["esaxx-rs@0.1.10"]["notices"]]
    assert "src/sais.hxx (header notice)" in header_notices
    assert any(
        n["path"] == "oniguruma/COPYING" for n in crates["onig_sys@69.9.1"]["notices"]
    )
    for text in (LEGAL / "rust-crates" / "texts").iterdir():
        assert hashlib.sha256(text.read_bytes()).hexdigest() == text.stem


def test_rust_coverage_fails_closed(tmp_path: Path) -> None:
    compliance = load("compliance")
    assert compliance.rust_notice_coverage(tmp_path, VERSIONS)[1]
    shutil.copytree(LEGAL / "rust-crates", tmp_path / "rust-crates")
    gaps = compliance.rust_notice_coverage(
        tmp_path, {**VERSIONS, "tokenizers": "0.23.0"}
    )[1]
    assert any("tokenizers 0.22.2" in gap for gap in gaps)
    victim = next((tmp_path / "rust-crates" / "texts").iterdir())
    victim.write_bytes(b"changed")
    assert any(
        "missing or changed" in gap
        for gap in compliance.rust_notice_coverage(tmp_path, VERSIONS)[1]
    )
    data = index()
    data["crates"][0]["notices"] = []
    (tmp_path / "rust-crates" / "index.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    assert any(
        "without a licence text" in gap
        for gap in compliance.rust_notice_coverage(tmp_path, VERSIONS)[1]
    )


def test_intel_record_pins_the_shipped_dlls_and_keeps_terms_open() -> None:
    record = json.loads((LEGAL / "intel-openmp" / "provenance.json").read_text())
    assert record["provenance"]["wheel"].startswith("intel_openmp-2026.1.0-")
    assert set(record["files"]) == {
        "_internal/torch/lib/libiomp5md.dll",
        "_internal/torch/lib/libiompstubs5md.dll",
    }
    licence = record["license"]
    for key in ("text", "third_party_notices"):
        data = (LEGAL / "intel-openmp" / licence[key]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == licence[key + "_sha256"]
    assert record["redistribution"]["status"].startswith("OPEN")


@pytest.mark.parametrize("matching", [True, False])
def test_intel_status_matches_dlls_but_never_settles_the_terms(
    tmp_path: Path, matching: bool
) -> None:
    compliance = load("compliance")
    bundle, legal = tmp_path / "bundle", tmp_path / "legal"
    assert compliance.intel_openmp_status(bundle, legal) == ({"bundled": False}, [])
    lib = bundle / "_internal/torch/lib"
    lib.mkdir(parents=True)
    (lib / "libiomp5md.dll").write_bytes(b"synthetic runtime")
    assert compliance.intel_openmp_status(bundle, legal)[1] == [
        "Intel OpenMP has no recorded provenance or licence text"
    ]
    shutil.copytree(LEGAL / "intel-openmp", legal / "intel-openmp")
    record = json.loads((legal / "intel-openmp/provenance.json").read_text())
    if matching:
        record["files"]["_internal/torch/lib/libiomp5md.dll"]["sha256"] = (
            hashlib.sha256(b"synthetic runtime").hexdigest()
        )
    (legal / "intel-openmp/provenance.json").write_text(json.dumps(record))
    status, gaps = compliance.intel_openmp_status(bundle, legal)
    assert status["matches_provenance"] is matching
    assert status["texts_present"] is True
    assert gaps[-1] == compliance.B4_INTEL
    assert len(gaps) == (1 if matching else 2)


def crate(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"demo-1.0.0/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return stream.getvalue()


def test_only_licence_files_and_named_headers_are_read() -> None:
    notices = load("rust_notices")
    archive = crate(
        {
            "LICENSE-MIT": b"MIT text",
            "vendor/COPYING": b"BSD text",
            "src/license.rs": b"fn main() {}",
            "src/lib.rs": b"// code",
            "src/a.hxx": b"/*\n * Copyright (c) 2010 Example\n */\nint x;\n",
        }
    )
    assert notices.crate_notices(archive) == [
        ("LICENSE-MIT", b"MIT text"),
        ("vendor/COPYING", b"BSD text"),
    ]
    with_header = notices.crate_notices(archive, ("src/a.hxx",))
    assert (
        "src/a.hxx (header notice)",
        b"/*\n * Copyright (c) 2010 Example\n */\n",
    ) in (with_header)
    with pytest.raises(ValueError):
        notices.crate_notices(archive, ("src/missing.hxx",))
