"""B4 narrows on recorded licence texts; the Intel item closes only on decisions."""

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


def test_intel_record_pins_the_nuget_package_and_records_the_decisions() -> None:
    record = json.loads((LEGAL / "intel-openmp" / "provenance.json").read_text())
    source = record["source"]
    assert (source["channel"], source["package_id"], source["version"]) == (
        "nuget",
        "intelopenmp.redist.win",
        "2026.1.0.239",
    )
    assert source["sha512_base64"] and source["sha256"]
    assert "proof of origin" in source["author_signature"]["commitment"]
    assert set(record["files"]) == {
        "_internal/torch/lib/libiomp5md.dll",
        "_internal/torch/lib/libiompstubs5md.dll",
    }
    for item in record["files"].values():
        assert source["entries"][item["package_entry"]] == item["sha256"]
    licence = record["license"]
    assert licence["name"] == load("compliance").INTEL_LICENSE
    assert source["entries"]["license.txt"] == licence["text_sha256"]
    for key in ("text", "third_party_notices"):
        data = (LEGAL / "intel-openmp" / licence[key]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == licence[key + "_sha256"]
    # The old wheel EULA is recorded only as superseded, never as the basis.
    assert "Developer Tools" in record["superseded"]["basis"]
    assert not (LEGAL / "intel-openmp" / "LICENSE.txt").exists()
    assert "Developer Tools" not in licence["name"]
    redistribution = record["redistribution"]
    assert redistribution["status"].startswith("OWNER-ASSESSED")
    assert "not external legal certification" in redistribution["status"]
    assert redistribution["decisions"]["onetbb_third_party_file"].startswith(
        "LD6: not required"
    )
    assert redistribution["residual_risks"]


def test_intel_notice_scopes_the_reverse_engineering_term_to_intel_files() -> None:
    notice = (LEGAL / "intel-openmp" / "NOTICE.md").read_text(encoding="utf-8")
    assert "Copyright Intel Corporation." in notice
    assert "only to these two Intel files" in notice
    assert "not intended to limit the rights the GNU LGPL version 3" in notice
    assert "intel-openmp/NOTICE.md" in (LEGAL / "QT_NOTICE.md").read_text(
        encoding="utf-8"
    )
    from social_text_intelligence.desktop.license_notice import qt_notice_text

    text = qt_notice_text("6.11.2")
    assert "forbid reverse engineering those two files only" in text


def synthetic_package(
    path: Path, entries: dict[str, bytes], extra: tuple[str, bytes] | None = None
) -> dict[str, Any]:
    import base64
    import zipfile

    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
        if extra:
            archive.writestr(*extra)
    data = path.read_bytes()
    return {
        "channel": "nuget",
        "package_id": "synthetic.redist",
        "version": "1.0.0",
        "filename": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512_base64": base64.b64encode(hashlib.sha512(data).digest()).decode(),
        "entries": {n: hashlib.sha256(d).hexdigest() for n, d in entries.items()},
    }


DLL = "runtimes/win-x64/native/libiomp5md.dll"
STUBS = "runtimes/win-x64/native/libiompstubs5md.dll"
PACKAGE = {DLL: b"synthetic runtime", STUBS: b"synthetic stubs", "license.txt": b"L"}


def test_the_pinned_package_yields_its_entries(tmp_path: Path) -> None:
    compliance = load("compliance")
    source = synthetic_package(tmp_path / "p.nupkg", PACKAGE)
    assert compliance.intel_package_entries(tmp_path / "p.nupkg", source) == PACKAGE


@pytest.mark.filterwarnings("ignore:Duplicate name")
@pytest.mark.parametrize(
    "fault", ["missing", "size", "sha256", "sha512", "entry", "absent", "duplicate"]
)
def test_an_unpinned_or_altered_package_is_refused(tmp_path: Path, fault: str) -> None:
    compliance = load("compliance")
    package = tmp_path / "p.nupkg"
    source = synthetic_package(package, PACKAGE)
    if fault == "missing":
        package.unlink()
    elif fault == "size":
        source["bytes"] += 1
    elif fault == "sha256":
        source["sha256"] = "0" * 64
    elif fault == "sha512":
        source["sha512_base64"] = "A" * 88
    elif fault == "entry":
        source["entries"][DLL] = "0" * 64
    elif fault == "absent":
        source["entries"]["runtimes/win-x64/native/other.dll"] = "0" * 64
    else:
        source = synthetic_package(package, PACKAGE, (DLL, b"second copy"))
    with pytest.raises(ValueError):
        compliance.intel_package_entries(package, source)


def synthetic_record(tmp_path: Path) -> Path:
    source = synthetic_package(tmp_path / "p.nupkg", PACKAGE)
    record = {
        "files": {
            "_internal/torch/lib/libiomp5md.dll": {
                "sha256": source["entries"][DLL],
                "package_entry": DLL,
            },
            "_internal/torch/lib/libiompstubs5md.dll": {
                "sha256": source["entries"][STUBS],
                "package_entry": STUBS,
            },
        },
        "source": source,
    }
    path = tmp_path / "provenance.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def torch_lib(tmp_path: Path, runtime: bytes = PACKAGE[DLL]) -> Path:
    lib = tmp_path / "bundle/_internal/torch/lib"
    lib.mkdir(parents=True)
    (lib / "libiomp5md.dll").write_bytes(runtime)
    (lib / "libiompstubs5md.dll").write_bytes(PACKAGE[STUBS])
    return tmp_path / "bundle"


def test_the_build_ships_the_nuget_copies(tmp_path: Path) -> None:
    build = load("build")
    record = synthetic_record(tmp_path)
    bundle = torch_lib(tmp_path)
    receipts = build.source_intel_openmp(bundle, tmp_path, record)
    assert [r["source"].split(": ")[1] for r in receipts] == [DLL, STUBS]
    assert (bundle / "_internal/torch/lib/libiomp5md.dll").read_bytes() == PACKAGE[DLL]


@pytest.mark.parametrize("fault", ["different-torch-build", "no-package", "absent"])
def test_the_build_stops_rather_than_mixing_intel_builds(
    tmp_path: Path, fault: str
) -> None:
    build = load("build")
    record = synthetic_record(tmp_path)
    bundle = torch_lib(
        tmp_path, b"other build" if fault == "different-torch-build" else PACKAGE[DLL]
    )
    if fault == "no-package":
        (tmp_path / "p.nupkg").unlink()
    if fault == "absent":
        (bundle / "_internal/torch/lib/libiompstubs5md.dll").unlink()
    with pytest.raises(ValueError):
        build.source_intel_openmp(bundle, tmp_path, record)
    if fault == "different-torch-build":
        shipped = bundle / "_internal/torch/lib/libiomp5md.dll"
        assert shipped.read_bytes() == b"other build"


@pytest.mark.parametrize("copy", ["nuget", "other"])
def test_the_packet_accepts_only_the_nuget_copies(tmp_path: Path, copy: str) -> None:
    compliance = load("compliance")
    record = synthetic_record(tmp_path)
    (tmp_path / "legal/intel-openmp").mkdir(parents=True)
    shutil.copyfile(record, tmp_path / "legal/intel-openmp/provenance.json")
    bundle = torch_lib(tmp_path, PACKAGE[DLL] if copy == "nuget" else b"other")
    if copy == "nuget":
        compliance.verify_intel_source(bundle, tmp_path, tmp_path / "legal")
    else:
        with pytest.raises(ValueError):
            compliance.verify_intel_source(bundle, tmp_path, tmp_path / "legal")


@pytest.mark.parametrize("variant", ["nuget", "wheel-eula", "mismatch"])
@pytest.mark.parametrize("decided", [False, True])
def test_intel_item_closes_only_on_decisions_for_matching_nuget_copies(
    tmp_path: Path, variant: str, decided: bool
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
    path = legal / "intel-openmp/provenance.json"
    record = json.loads(path.read_text())
    if variant != "mismatch":
        record["files"]["_internal/torch/lib/libiomp5md.dll"]["sha256"] = (
            hashlib.sha256(b"synthetic runtime").hexdigest()
        )
        record["source"]["entries"][DLL] = hashlib.sha256(
            b"synthetic runtime"
        ).hexdigest()
    if variant == "wheel-eula":
        record["source"]["channel"] = "pypi"
    path.write_text(json.dumps(record))
    status, gaps = compliance.intel_openmp_status(bundle, legal, decided=decided)
    assert status["matches_provenance"] is (variant != "mismatch")
    assert status["nuget_source_recorded"] is (variant != "wheel-eula")
    closes = decided and variant == "nuget"
    assert status["owner_assessed"] is closes
    if closes:
        assert gaps == []
    else:
        assert gaps[-1] == compliance.B4_INTEL
        assert len(gaps) == (1 if variant == "nuget" else 2)


@pytest.mark.parametrize(
    "fault", ["none", "other-package", "no-notice", "changed-notice", "changed-licence"]
)
def test_decisions_do_not_cover_another_package_or_missing_notices(
    tmp_path: Path, fault: str
) -> None:
    compliance = load("compliance")
    bundle, legal = tmp_path / "bundle", tmp_path / "legal"
    shutil.copytree(LEGAL / "intel-openmp", legal / "intel-openmp")
    path = legal / "intel-openmp/provenance.json"
    record = json.loads(path.read_text())
    lib = bundle / "_internal/torch/lib"
    lib.mkdir(parents=True)
    for shipped, item in record["files"].items():
        item["sha256"] = hashlib.sha256(shipped.encode()).hexdigest()
        record["source"]["entries"][item["package_entry"]] = item["sha256"]
        (bundle / shipped).write_bytes(shipped.encode())
    if fault == "other-package":
        record["source"]["sha256"] = "0" * 64
    if fault == "no-notice":
        (legal / "intel-openmp/NOTICE.md").unlink()
    if fault == "changed-notice":
        with (legal / "intel-openmp/NOTICE.md").open("ab") as notice:
            notice.write(b" Intel terms also apply to the Qt libraries.")
    if fault == "changed-licence":
        (legal / "intel-openmp/INTEL-SIMPLIFIED-SOFTWARE-LICENSE.txt").write_bytes(b"x")
    path.write_text(json.dumps(record))
    status, gaps = compliance.intel_openmp_status(bundle, legal, decided=True)
    assert status["owner_assessed"] is (fault == "none")
    assert (gaps == []) is (fault == "none")
    if fault != "none":
        assert gaps[-1] == compliance.B4_INTEL


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
