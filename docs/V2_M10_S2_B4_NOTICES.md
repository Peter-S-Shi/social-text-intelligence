# V2 M10 S2 — B4 licence materials

Status: **S2 COMPLETE on `main` (PR #65).** The independent review accepted the
engineering. **B4 stays OPEN**, narrowed to one item: Intel OpenMP redistribution
authorization, which is **not approved**.
- The packet now carries licence texts for every Rust crate in the pinned source
  superset, plus Intel's licence for the shipped OpenMP DLLs.
- Binary distribution remains **BLOCKED**, and `distribution_permitted` stays
  false. Nothing was published; PR #65 merges only with owner approval.

Plan: [Core + Optional Components plan, revision 2](V2_M10_CORE_OPTIONAL_PLAN.md)
§5 and §6 (S2). The owner approved it on 2026-10-11, with metadata lookups, the
checksum-pinned crates.io archives, and one intel-openmp wheel once its relevance
was established.

## 1. Inventory correction

tokenizers' `bindings/python/Cargo.lock` at `v0.22.2` has **149 entries**. Two of
them, `tokenizers` and `tokenizers-python` 0.22.2, are workspace packages with no
crates.io checksum. That leaves **147 crates.io archives**. The licence for the
workspace pair comes from the tokenizers repository at the tag commit
`f383101a26663708484cac0727792aad74f78234`. The `Cargo.lock` fetched from that
commit reproduces the receipt's `lockfile_sha256`.

safetensors 0.8.0 also compiles Rust crates into `_safetensors_rust.pyd`. Its
wheel-embedded CycloneDX SBOM pins 31 crates by SHA-256, 24 of them not in the
tokenizers set. They are the same kind of checksum-pinned crates.io archive, and
B4 cannot close without them, so they are included.

## 2. Rust crates (closed for the packet)

`tools/m10/rust_notices.py` builds `distribution/legal/rust-crates/`:

- **171 crates.io archives** were downloaded into a local cache (about 22 MB, not
  committed). Each matched its pinned SHA-256 before use.
- Only licence and copyright files are read from each archive (`LICENSE*`,
  `COPYING*`, `COPYRIGHT*`, `NOTICE*`, `UNLICENSE*`, including vendored ones such
  as `onig_sys/oniguruma/COPYING`). Nothing is extracted to disk, and no source
  archive is committed.
- `esaxx-rs` vendors C++ (`esa.hxx`, `sais.hxx`) whose MIT notices, with their
  copyright lines, exist only in the file headers. Those header comments are
  included.
- **173 index entries:** 147 crates from the tokenizers lock, 24 added by the
  safetensors SBOM, and the 2 workspace packages. They point to **101 unique texts
  (about 0.7 MB)**, stored by SHA-256. The texts are kept byte-exact in Git
  (`.gitattributes -text`).
- **Priority coverage:** all 38 crates recovered from `tokenizers.pyd` and all 7
  from `_safetensors_rust.pyd` (M10-E1 evidence) have texts.
- **No text, recorded as not linked on Windows:** `r-efi` and `wasip2`. In
  getrandom's `Cargo.toml` they are dependencies only for UEFI and WASI targets.
- Some upstream copyright lines include their authors' published email addresses.
  They are kept verbatim because the licences require the notices to be
  reproduced unchanged.

## 3. Intel OpenMP (provenance closed; terms OPEN)

- **Version and provenance.** PyTorch 2.13.0 ships `torch/lib/libiomp5md.dll`
  (1,617,536 bytes, FileVersion 20260213) and `libiompstubs5md.dll` (44,160 bytes).
  - Each candidate wheel's zip index was read with an HTTP range request, without
    downloading the wheel. Only intel-openmp **2026.1.0** for win_amd64 matched
    both files by size and CRC-32. 2025.3.2, 2025.3.3 and 2026.0.0 did not.
  - The one approved download, `intel_openmp-2026.1.0-py2.py3-none-win_amd64.whl`
    (26,355,044 bytes), matched PyPI's SHA-256 `8f9f86d9…7206`.
  - Its two DLLs are **byte-identical (SHA-256)** to those in the frozen bundle.
- **Build route.** In PyTorch `v2.13.0`, `.ci/pytorch/windows/setup_build.bat`
  installs `mkl-static`, which requires `intel-openmp`.
  `cmake/PostBuildSteps.cmake` then installs both DLLs into `torch/lib`.
- **Terms.** The wheel's licence is the *Intel End User License Agreement for
  Developer Tools (Version August 2024)*. It and the wheel's
  `third-party-programs.txt` now ship in `legal/intel-openmp/`, with
  `provenance.json`.
- **Unresolved, and engineering cannot settle it** (owner/legal decision):
  1. Under §2.1.D, only "Redistributables" listed in `redist.txt` or a
     similarly named file may be distributed. The wheel contains no such list, so
     the DLLs' Redistributable status is not established.
  2. Under §2.1.D(2), executable Redistributables may be distributed only under a
     licence that prohibits reverse engineering. STI has no such end-user terms.
  3. Under §2.1.D(4)(v), the distributor must indemnify and defend Intel.
  4. Under §7.3, Intel's limitations of liability must be made binding on the
     customers who receive the Redistributables.

  As with R2, an independently downloadable package is not assumed to move these
  obligations onto users.
- **Review position (2026-10-11).** The official PyPI wheel does not by itself
  confer redistribution rights. The owner accepting the indemnity would not
  substitute for a verified Redistributables designation.
- **One official-source check (2026-10-11): unresolved.** Intel's page
  "Intel® oneAPI DPC++/C++ and Fortran Compilers Runtime Libraries by Version"
  (article 662585, updated 2025-05-01) is the official index of redistributable
  compiler runtimes.
  - Its newest Windows entry is 2025.2.1. It has no 2026.1 entry.
  - It does not name `libiomp5md.dll`, `libiompstubs5md.dll` or OpenMP, and does
    not list the files inside any package.
  - It states no redistribution terms, and does not mention PyPI or
    `intel-openmp`.

  No further Intel investigation, alternative packaging or PyTorch rebuild was
  started. The unresolved item is precise: no official Intel source has been
  found that designates the exact `intel-openmp` 2026.1.0 Windows DLLs as
  Redistributables, or that states their downstream terms.

## 4. PyTorch static third-party code

This is unchanged at the level set by the approved plan (§5): the torch wheel's
upstream `third_party` licence superset, which the packet already ships. The
packet records it as a separate entry.

## 5. Packet derivation

`tools/m10/compliance.py` now derives B4 from `b4_coverage.remaining`:

- the Rust index must match the bundled tokenizers and safetensors versions, with
  every indexed text present and unchanged, and every crate covered or recorded
  as not linked on Windows;
- the Intel DLLs in the bundle must match `provenance.json`, with both licence
  texts present. Even then, the redistribution item is always added;
- the torch notices must be present.

B4 keeps its general wording when no coverage check runs, so it fails closed.
Other blockers are unchanged.

## 6. Verification

| Check | Result |
| --- | --- |
| Frozen build at `fbb6e13` (official CPython 3.13.16) | 5,360 files; no `model.npz.xz` |
| Packet | valid; blockers **B1** and **B4**, and B4 names only the Intel OpenMP item; `b4_coverage.rust_crates.complete: true` (173 crates, 101 texts); Intel DLLs match the provenance record; 107 PyTorch notice files |
| `--verify-runtime` / `--smoke` / `--license-info` | exit 0; `distribution_permitted: false` |
| Opt-in frozen pytest (`STI_M10_BUNDLE`) | 2 passed |
| Local full suite | 1,262 passed, 6 opt-in skipped; Ruff and strict MyPy pass |
| PR CI | implementation head `fbb6e13`: 4 checks passed |
| Installer | not rebuilt; this change touches only the packet, which the installer copies |
| Clean-machine matrix | NOT RUN (S5) |

Evidence: [s2-packet-receipt.json](evidence/m10-s2/s2-packet-receipt.json).

## 7. Still open

- **B4:** a verified Redistributables designation for the exact Intel OpenMP
  2026.1.0 Windows DLLs, from Intel or legal counsel, and then an owner/legal
  decision on the conditions above with end-user terms that cover them. Otherwise
  another route needs its own approval.
- B1 (S4), B6 (S3), and the clean-machine matrix (S5), as before. B5's
  training-corpus terms stay unverified. R2 stays parked in draft PR #62.
