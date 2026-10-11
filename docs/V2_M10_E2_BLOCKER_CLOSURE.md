# M10-E2 — Distribution Blocker Closure Engineering

## Authority and boundary

Owner-authorized from `main@1f2132cfba01009f8f3aec1bbc98e44cfc9a5830`, the merged
M10-E1 result. The end product is still a legally distributable Windows `.exe`
installer for ordinary users.

This milestone changes packaging inputs only:

- the build interpreter;
- which third-party files are shipped;
- one import-name edit in two NumPy binaries;
- the installer's prerequisite check;
- the shipped notices.

`src/` is unchanged. PySide6, PyInstaller and Inno Setup are retained. No binary
is published, and `distribution_permitted` stays `false` in every generated
record. Clean-machine validation, formal Windows UAT, accessibility acceptance,
signing/SmartScreen and the owner's optional 30-minute smoke remain **NOT RUN**
or open. M9.2–M9.4 remain deferred, and the open M9.2-A PR is untouched.

The owner approved these downloads, all kept under ignored `_local/` and not
committed:

- the python.org CPython 3.13.16 NuGet package;
- the 43 pinned cp313 build wheels from PyPI;
- the official Qt 6.11.2 qttranslations archive;
- read-only GitHub and crates.io metadata.

The owner chose CPython 3.13.16. The newest official binary of 3.12 is 3.12.10,
which lacks later security fixes.

## 1. Blocker status after M10-E2

| ID | Status | What changed | Next responsible action |
| --- | --- | --- | --- |
| B1 | **OPEN — narrowed to an owner/legal position** | All 121 shipped Qt files are VERIFIED against official Qt build SBOMs: 25 binaries and all 96 translation files (§2.3). The delivered `pyside-setup` source equals the upstream `v6.11.2` tag tree (§2.3) | Owner/legal: (a) accept the upstream-tagged release source and its build scripts as the Corresponding Source for the unmodified upstream binding binaries, **or** rebuild the bindings with the E4 toolchain; and (b) confirm the same-page source route (M10-E1 §4) |
| B2 | **CLOSED** (retained from M10-E1) | The software renderer is still absent from the final build | — |
| B3 | **CLOSED** (licence and provenance; route validation pending the clean-machine matrix) | The runtime is the official PSF CPython 3.13.16, checked file by file at build time. No Microsoft Visual C++ runtime file is shipped; the per-user installer requires the system runtime and never elevates. The packet no longer derives a B3 blocker (§2.1–2.2) | Optional owner decision R2 in §2.2. Operational checks belong to the clean-machine gate |
| B4 | **OPEN — narrowed** | `hf_xet` (73 compiled crates, including AWS-LC) and PyTorch's `protoc.exe` are removed. tokenizers has an exact `Cargo.lock` receipt (149 locked crates). NumPy's bundled-library licences are confirmed (§2.4) | Engineering, with owner download approval: tokenizers crate licence texts, and the Intel OpenMP licence for PyTorch's `libiomp5md`/`libiompstubs5md`. PyTorch's static third-party content stays at the upstream-notice level |
| B5 | **OPEN — owner/legal decision** | Verified distribution rights are separated from the unresolved corpus terms (§2.5) | Owner/legal decides on the model; replacement options are in §2.5. Attribution or owner risk acceptance alone is not clearance |
| B6 | **OPEN** | Coherent-set replacement still PASSES on the new bundle. E4 is prepared and checked against real evidence (§2.6) | Owner installs VS 2022 Build Tools (MSVC v143 14.44) and a Windows 11 SDK and accepts the licence; engineering then runs `tools/m10/e4_modified_qt.ps1` |

The final build's packet derives exactly **B1 (narrowed), B4 and B5**
([build receipt](evidence/m10-e2/e2-build-receipt.json)). B6 is tracked in this
record.

## 2. Evidence

### 2.1 Official CPython runtime (B3)

- **Package:** the python.org NuGet package `python` 3.13.16 from nuget.org.
  - Its SHA-512 matches nuget.org's published `packageHash`.
  - SHA-256 `95fad176…4c34`, published 2026-09-30.
  - `python.exe` and `python313.dll` carry valid Python Software Foundation
    Authenticode signatures, and the build string is `tags/v3.13.16:cbc944f`.
  - No installer was run and no registry entries were written: the package was
    extracted, and a venv was created at a short path.
- **Manifest:** [`distribution/python-runtime.json`](../distribution/python-runtime.json)
  pins 29 runtime files. That covers the interpreter, `python3.dll` and
  `python313.dll`, every `DLLs/` extension and runtime library (OpenSSL 3.5.9,
  libffi, SQLite and others), and `LICENSE.txt`.
- **Build-time check:** `build.py` requires Python 3.13 and refuses an
  interpreter whose files differ from the manifest.
- **Packet check:** the packet compares every bundled CPython native file and the
  shipped licence with the manifest. Final build: **24 files matched**,
  0 unpinned, licence matched (`python_runtime.verified: true`).
- **Licences:** the official `LICENSE.txt` carries the PSF terms and the notices
  for the runtime's bundled libraries.

### 2.2 Microsoft Visual C++ runtime (B3)

**What was shipped before.** M10-E1 shipped these Microsoft runtime files:

- copies taken from the build host's `System32`;
- the interpreter's `vcruntime140*.dll`;
- the Qt-signed copies in `PySide6/` and `shiboken6/`;
- NumPy's delvewheel-renamed `msvcp140-<hash>.dll`.

Imports in the shipped binaries need `vcruntime140.dll`, `vcruntime140_1.dll`
and `msvcp140.dll`, plus `msvcp140_1.dll`/`msvcp140_2.dll` for PySide6. Nothing
imported `MSVCP140_ATOMIC_WAIT.dll`.

**Microsoft's terms** (Microsoft Learn pages read 2026-10-11 during M10-E1, §2.3):

- Redistribution of the runtime is limited to licensed Visual Studio users.
- Files must come from a licensed installation's `VC\redist` folder.
- The recommended route is the official `vc_redist.x64.exe`, a machine-wide
  installer.

**Routes compared:**

| Route | Licence needed | Admin rights | Result |
| --- | --- | --- | --- |
| R1: require the system runtime (implemented) | None: STI ships no Microsoft file | Not for STI. A user who lacks the runtime installs Microsoft's package, which may need admin | Chosen |
| R2: app-local DLLs from a licensed `VC\redist` | The owner's own valid VS licence (unconfirmed) | None | Not done: it would rely on an unconfirmed licence |
| R3: bundle or chain `vc_redist.x64.exe` | VS licence; machine-wide install | Yes; this conflicts with the fixed per-user, non-admin installer | Rejected |

**Implementation:**

- **Spec:** omits every `msvcp140*`, `vcruntime140*`, `concrt140` and
  `vccorlib140` DLL.
- **Build:**
  - Relinks the delvewheel-renamed `msvcp140-a4c2…dll` import in two NumPy
    binaries back to `msvcp140.dll`. This is the same in-place import-name edit
    delvewheel made; NumPy is BSD-3. Both edits have before/after hashes in the
    build evidence.
  - Refuses any remaining runtime file or vendored import.
  - Check run against the real NumPy package: with the vendored copy deleted,
    the relinked NumPy 2.5.1 imported and computed correctly against the system
    runtime.
- **Installer generator:** refuses any runtime file.
- **Installer:**
  - Keeps `PrivilegesRequired=lowest`.
  - Its `InitializeSetup` reads the HKLM64 Visual C++ 14.0 x64 registration and
    requires 14.44 or later, the toolset of Qt 6.11.2 and CPython 3.13.16.
  - If the runtime is missing, setup stops, logs the reason and offers to open
    Microsoft's download page. It never downloads, bundles or elevates.
- **Final build:** no Microsoft runtime file; DLL closure 87 binaries, none
  unresolved. The host has runtime 14.51 installed, so the system copy satisfies
  the imports.

**Owner decision (optional, does not block closure).** R2 would let users who
lack the runtime install STI without admin rights. It requires the owner to hold
a valid Visual Studio licence and to take the files from that installation's
`VC\redist`. **Recommendation:** release with R1. Consider R2 only if clean-machine
testing shows the prerequisite is a real barrier.

### 2.3 Qt translations and binding source (B1)

- **Translations:**
  - The official Qt 6.11.2 qttranslations archive was downloaded with owner
    approval, and its SHA-1 matched Qt's published checksum.
  - All **96/96** shipped `.qm` files are byte-identical to it
    ([comparison](evidence/m10-e2/translations-official-comparison.json)).
  - Its CC0 SBOM is now pinned in the provenance manifest and staged by the
    build. The verifier checks `translations/*.qm` by plain SHA-1, and accepts
    an SBOM listing a file twice only when both entries are identical.
  - Final build: **121 VERIFIED, 0 uncovered**. QtBase and QtSvg link by commit;
    QtImageFormats and QtTranslations link by version only.
- **Binding source:** the delivered `pyside-setup-everywhere-src-6.11.2.tar.xz`
  was compared, file by file by git blob hash, with the upstream mirror's
  `v6.11.2` tag tree, commit `24627cd36e1593adf22eb1f2950e4248e7bcc1ec`
  ([receipt](evidence/m10-e2/pyside-source-correspondence.json)).
  - 4,600 of 4,602 files are identical.
  - The other two are git symlinks, which the archive stores as file copies.
  - Four `.gitattributes`/`.gitignore` files are not exported.
- **What remains:** the wheels' binding binaries carry no build record, so
  byte-level producer correspondence cannot be shown without rebuilding them.

### 2.4 Compiled-dependency licences (B4)

- **Removed (no product path):**
  - `hf_xet` serves only Xet-backed Hugging Face downloads; the app downloads
    models with its own client and loads local folders. With `hf_xet` made
    unimportable, the opt-in real-model test (import, verify and offline analysis
    of both pinned models) **passed**.
  - `torch/bin/protoc.exe` is a build tool that nothing executes.
  - Final build: 87 native binaries, down from 102, with both items absent.
- **tokenizers:** the receipt uses `bindings/python/Cargo.lock` at `v0.22.2`
  ([receipt](evidence/m10-e2/tokenizers-crates.json)).
  - 149 locked crates, each with its crates.io checksum and licence expression.
  - All 38 crates found in the binary are in the lock.
  - Every licence is permissive or offers a permissive choice: mostly
    MIT/Apache-2.0, with BSD-2-Clause, Unlicense, Zlib and Unicode-3.0.
  - Open: these are expressions, not the licence texts with copyright lines.
- **Unchanged:**
  - safetensors' CycloneDX SBOM is still preserved.
  - NumPy's bundled `LICENSE.txt` covers its vendored OpenBLAS, LAPACK and GCC
    runtime.
- **Still open:**
  - PyTorch ships Intel-signed `libiomp5md.dll` and `libiompstubs5md.dll`, and
    no Intel licence text is in the packet.
  - PyTorch's statically linked third-party code is covered only by the upstream
    `third_party` licence superset.

### 2.5 py3langid model (B5)

**Verified.** The package is BSD-3-Clause (fork, Copyright 2021 Adrien
Barbaresi) over BSD-2-Clause (original, Marco Lui). The licence text is shipped.
The model file `model.npz.xz` is distributed by its author inside that package.
Neither the README nor the LICENSE at `v0.4.0` states a separate model licence.

**Not verified — the corpus terms behind the model** (per-source pages, read
2026-10-11):

| Corpus | What the source page states |
| --- | --- |
| Wikipedia | Text under CC BY-SA (4.0 or later for modifications) and GFDL |
| Tatoeba | Default CC BY 2.0 FR; licences vary per sentence and may add NC, ND or SA conditions |
| CC-100 | "No claims of intellectual property"; no licence named |
| Glot500 | "We don't own any part of the data"; CC0 covers only packaging and metadata; source licences are listed elsewhere |
| GlotSparse | Same position as Glot500; access is gated |
| Leipzig Corpora | Terms page could not be read (anti-bot challenge) |
| GlotCC-V1 | Terms page could not be read (card body not rendered) |

Whether such terms bind a statistical n-gram model trained on the text — for
example share-alike or non-commercial conditions — is a legal question. This
milestone does not answer it. Attribution satisfies only the BSD notice terms,
and owner risk acceptance is not legal clearance.

**Minimally disruptive replacement, only if legal review rejects the model.** The
language check is a single English-or-not warning (M5.6). The narrowest options:

1. Retrain with py3langid's own deterministic pipeline, using only sources whose
   licences legal review accepts. The API and code are unchanged; only the model
   file changes.
2. Swap in a component whose model carries an explicit licence. That needs a new
   dependency and its own evaluation.

### 2.6 B6 replacement and the prepared E4

- **Replacement still works.** On the new bundle, a coherent swap to the upstream
  6.11.1 PySide6/shiboken6 wheels (36 files; no Microsoft files to swap) PASSES:
  - `--license-info` reports Qt **6.11.1**;
  - the runtime check and smoke pass;
  - 0 Qt imports are unresolved
  ([receipt](evidence/m10-e2/replacement-e2c.json)).
- **E4 script.** [`tools/m10/e4_modified_qt.ps1`](../tools/m10/e4_modified_qt.ps1)
  implements M10-E1 §5. It:
  1. checks prerequisites read-only: MSVC 19.44, CMake ≥ 3.30.5, Ninja, `rc.exe`,
     the pinned QtBase archive hash and a fresh work directory;
  2. applies one patch in `qt_build_string()` (`STI-E4-MODIFIED`) and refuses if
     the source differs;
  3. builds QtCore;
  4. replaces it in a copy of the bundle, requiring the marker and a changed hash;
  5. runs the import check and the three frozen checks;
  6. writes a receipt.

  It never installs, downloads or accepts a licence. Without MSVC it stops with
  exit code 3 and creates nothing (tested).
- **Import checker.** [`tools/m10/e4_check.py`](../tools/m10/e4_check.py) is a
  dependency-free checker for unresolved Qt imports. Against real evidence it
  gives:
  - **0** on the working bundle;
  - **1** on the M10-B 6.11.1 Qt-only swap;
  - **2** on the 6.12.0 Qt-only swap.

  These match the M10-E1 analysis.

## 3. Final build, installer and validation

- **Final Windows build** at `ba2887bd84ad8dfafbe580b0bbb4b8aa4cdcb4ce`, under
  CPython 3.13.16 with the 43 pinned packages:
  - layout: 5,256 files / 728,293,371 bytes; 6,675 PYZ modules; 87 native
    binaries; model weights not bundled;
  - packet: valid, with blockers B1 (narrowed), B4 and B5;
  - the earlier builds at `8e7c070` and `d3934be` gave the same results; the
    final build adds the review fixes (delay-load relink, shared checks and the
    trimmed component register);
  - the coherent 6.11.1 replacement was repeated on this final bundle and
    passed.
- **Frozen checks:** `--license-info`, `--verify-runtime` and `--smoke` exit 0
  (native Windows Qt window). The opt-in frozen pair: **2 passed**. DLL closure
  and Qt import check: none unresolved.
- **Installer:** compiled with the pinned Inno Setup 6.7.3 from the final bundle
  ([receipt](evidence/m10-e2/installer-receipt.json)): 730,747,718 bytes,
  per-user, runtime check present, no Microsoft runtime entries.
  - **Host install lifecycle: NOT RUN.** An existing per-user STI installation
    occupies the fixed location, and the validator needs a fresh namespace, so
    it was not overwritten.
  - **Missing-runtime branch: NOT RUN.** It needs a machine without the runtime.
  - Both belong to the clean-machine matrix.
- **Tests:** regressions for the runtime manifest check, import-table parsing and
  relinking, refusal of runtime files, the installer's prerequisite and refusal,
  translation verification, CPython verification, evidence-derived B3, and E4.
- **Static checks:** Ruff and strict MyPy pass. Full-suite and CI results are in
  `PROJECT_STATUS.md`.
- **Independent review fixes** (Standards and Spec, before the final build):
  - Delay-load imports are now read and relinked; before, a delay-loaded
    vendored runtime would have passed the check.
  - The E4 script no longer fails under Windows PowerShell 5.1 when `cl.exe`
    is present. This was checked with stub compilers reporting 19.38 and
    19.44.
  - The CPython licence check reads the shipped copy.
  - `concrt140`/`vccorlib140` are owned as Microsoft runtime.
  - The spec reuses the build's runtime pattern, and the E4 checker shares
    the build's PE parser.
  - The component register no longer lists the unshipped `hf-xet` and
    `pytest`.
- **Not run:** frozen model inference. Source-mode inference without `hf_xet`
  passed.

**Building now** (replaces the M10-A Python 3.12 instructions):

1. Extract the pinned python.org NuGet package (check its SHA-256 first). Create
   a venv at a short path with its `tools\python.exe`.
2. `pip install --only-binary :all: -r tools\m10\requirements-build.txt`
3. `python tools\m10\build.py --output X:\sti-build --source-dir X:\sources`

The source directory also needs the four Qt SBOMs.

## 4. Path to the distributable installer

1. **Owner decisions:**
   - the B1 binding-source position and same-page source route;
   - the B5 model;
   - optionally R2 for the runtime.
2. **Owner toolchain install → E4 run (B6).** If the bindings are to be rebuilt,
   the same toolchain covers B1(a).
3. **B4 notice completion:** tokenizers crate texts, the Intel OpenMP licence,
   and the PyTorch static-content review.
4. **Disposable VM / Windows Sandbox matrix:** C01–C16, including the
   missing-runtime prompt and real model download/inference.
5. **Code signing / SmartScreen decision**, then the owner's release decision.
