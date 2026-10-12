"""Collect licence texts for the Rust crates compiled into the frozen bundle (B4).

The crate set is a source superset: every crates.io package in tokenizers'
pinned `Cargo.lock` receipt and in safetensors' wheel-embedded CycloneDX SBOM.
Each `.crate` archive is downloaded once into a local cache, checked against its
pinned SHA-256, and only licence/copyright files are read out of it (nothing is
extracted to disk). Texts are stored by content hash, so identical texts are kept
once, beside an index that maps every crate to its texts.

The two tokenizers workspace packages have no crates.io archive; their licence
comes from the tokenizers repository at the pinned `v0.22.2` commit.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
import time
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/evidence/m10-e2/tokenizers-crates.json"
COMPILED = ROOT / "docs/evidence/m10-e1/rust-compiled-crates.json"
OUTPUT = ROOT / "distribution/legal/rust-crates"
CRATE_URL = "https://static.crates.io/crates/{name}/{name}-{version}.crate"
TOKENIZERS_COMMIT = "f383101a26663708484cac0727792aad74f78234"  # tag v0.22.2
TOKENIZERS_RAW = "https://raw.githubusercontent.com/huggingface/tokenizers/" + (
    TOKENIZERS_COMMIT
)
SAFETENSORS_SBOM = "safetensors-0.8.0.dist-info/sboms/safetensors-python.cyclonedx.json"
NOTICE_NAME = re.compile(
    r"^(licen[cs]e|copying|copyright|notice|unlicense)([-_.].*)?$", re.IGNORECASE
)
MAX_NOTICE_BYTES = 512 * 1024
# Vendored C/C++ whose copyright and permission notice is only in a file header.
HEADER_NOTICES = {"esaxx-rs": ("src/esa.hxx", "src/sais.hxx")}
# Locked crates that cannot be linked into a win_amd64 binary (getrandom's
# Cargo.toml gates them on these targets); their archives carry no licence file.
NOT_LINKED_ON_WINDOWS = {
    "r-efi": 'getrandom dependency only for cfg(target_os = "uefi")',
    "wasip2": (
        'getrandom dependency only for cfg(target_os = "wasi", target_env = "p2")'
    ),
}
USER_AGENT = "sti-compliance-notices (licence-text collection)"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        return bytes(response.read())


CODE_SUFFIXES = {
    ".rs",
    ".py",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".hxx",
    ".js",
    ".toml",
    ".json",
    ".yml",
    ".yaml",
    ".sh",
}


def is_notice(member: str) -> bool:
    path = PurePosixPath(member)
    return (
        bool(NOTICE_NAME.match(path.name)) and path.suffix.lower() not in CODE_SUFFIXES
    )


def header_notice(source: bytes) -> bytes:
    """The leading `/* ... */` comment, which holds the vendored file's notice."""
    text = source.decode("utf-8")
    start, end = text.find("/*"), text.find("*/")
    if start != 0 or end < 0 or "Copyright" not in text[:end]:
        raise ValueError("Expected a leading copyright comment.")
    return text[: end + 2].encode("utf-8") + b"\n"


def crate_notices(
    archive: bytes, headers: tuple[str, ...] = ()
) -> list[tuple[str, bytes]]:
    """Licence/copyright files in a `.crate`, by path below the crate root."""
    notices = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.size > MAX_NOTICE_BYTES:
                continue
            parts = PurePosixPath(member.name).parts
            relative = PurePosixPath(*parts[1:]).as_posix() if len(parts) > 1 else ""
            if relative and (is_notice(relative) or relative in headers):
                handle = tar.extractfile(member)
                if handle is not None:
                    data = handle.read()
                    if relative in headers:
                        notices.append(
                            (relative + " (header notice)", header_notice(data))
                        )
                    else:
                        notices.append((relative, data))
    if len([n for n in notices if n[0].endswith("(header notice)")]) != len(headers):
        raise ValueError("A required vendored header notice is missing.")
    return sorted(notices)


def crate_set(site_packages: Path) -> list[dict[str, object]]:
    """Every pinned crates.io package, with the binaries it is known to be in."""
    compiled = json.loads(COMPILED.read_text(encoding="utf-8"))["binaries"]
    found = {
        crate: binary
        for binary in ("tokenizers.pyd", "_safetensors_rust.pyd")
        for crate in compiled[binary]["crates"]
    }
    crates: dict[tuple[str, str], dict[str, object]] = {}

    def add(name: str, version: str, checksum: str, licence: str, owner: str) -> None:
        entry = crates.setdefault(
            (name, version),
            {
                "name": name,
                "version": version,
                "sha256": checksum,
                "license": licence,
                "owners": [],
                "found_in_binary": False,
            },
        )
        if entry["sha256"] != checksum:
            raise ValueError(f"Conflicting checksums for {name} {version}.")
        owners = entry["owners"]
        assert isinstance(owners, list)
        if owner not in owners:
            owners.append(owner)
        if f"{name}@{version}" in found:
            entry["found_in_binary"] = True

    for item in json.loads(RECEIPT.read_text(encoding="utf-8"))["packages"]:
        if item.get("checksum_sha256"):  # workspace packages have none
            add(
                item["name"],
                item["version"],
                item["checksum_sha256"],
                item["license"],
                "tokenizers 0.22.2",
            )
    sbom = json.loads((site_packages / SAFETENSORS_SBOM).read_text(encoding="utf-8"))
    for component in sbom["components"]:
        hashes = {h["alg"]: h["content"] for h in component.get("hashes", [])}
        if "SHA-256" not in hashes:
            continue  # the safetensors workspace crate itself; its LICENSE ships
        licence = " AND ".join(
            item.get("expression") or item["license"].get("id", "")
            for item in component.get("licenses", [])
        )
        add(
            component["name"],
            component["version"],
            hashes["SHA-256"],
            licence,
            "safetensors 0.8.0",
        )
    # The crates found in a binary first, so a partial run covers them.
    return sorted(
        crates.values(),
        key=lambda c: (not c["found_in_binary"], str(c["name"]), str(c["version"])),
    )


def collect(site_packages: Path, cache: Path, delay: float) -> dict[str, object]:
    texts = OUTPUT / "texts"
    texts.mkdir(parents=True, exist_ok=True)
    entries = []
    for crate in crate_set(site_packages):
        name, version = str(crate["name"]), str(crate["version"])
        local = cache / f"{name}-{version}.crate"
        if not local.is_file():
            local.write_bytes(fetch(CRATE_URL.format(name=name, version=version)))
            time.sleep(delay)
        archive = local.read_bytes()
        if sha256(archive) != crate["sha256"]:
            raise ValueError(f"{name} {version}: archive checksum mismatch.")
        notices = []
        for path, data in crate_notices(archive, HEADER_NOTICES.get(name, ())):
            digest = sha256(data)
            (texts / f"{digest}.txt").write_bytes(data)
            notices.append({"path": path, "sha256": digest})
        entry = dict(crate, source="crates.io", notices=notices)
        if name in NOT_LINKED_ON_WINDOWS:
            entry["not_linked_on_windows"] = NOT_LINKED_ON_WINDOWS[name]
        entries.append(entry)
    lock = fetch(f"{TOKENIZERS_RAW}/bindings/python/Cargo.lock")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if sha256(lock) != receipt["lockfile_sha256"]:
        raise ValueError("tokenizers Cargo.lock no longer matches the receipt.")
    licence = fetch(f"{TOKENIZERS_RAW}/LICENSE")
    digest = sha256(licence)
    (texts / f"{digest}.txt").write_bytes(licence)
    for workspace in ("tokenizers", "tokenizers-python"):
        entries.append(
            {
                "name": workspace,
                "version": "0.22.2",
                "sha256": None,
                "license": "Apache-2.0",
                "owners": ["tokenizers 0.22.2"],
                "found_in_binary": True,
                "source": f"github.com/huggingface/tokenizers@{TOKENIZERS_COMMIT}",
                "notices": [{"path": "LICENSE", "sha256": digest}],
            }
        )
    index = {
        "schema_version": 1,
        "scope": (
            "source superset: every crates.io package in tokenizers 0.22.2's "
            "Cargo.lock receipt and safetensors 0.8.0's CycloneDX SBOM, plus the "
            "tokenizers workspace packages"
        ),
        "binaries": {"tokenizers": "0.22.2", "safetensors": "0.8.0"},
        "crates": entries,
        "without_notice_text": sorted(
            f"{e['name']}@{e['version']}"
            for e in entries
            if not e["notices"] and "not_linked_on_windows" not in e
        ),
    }
    (OUTPUT / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-packages", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    index = collect(args.site_packages, args.cache, args.delay)
    crates = index["crates"]
    assert isinstance(crates, list)
    print(
        json.dumps(
            {"crates": len(crates), "without_notice_text": index["without_notice_text"]}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
