# M10-E1 — Practical Binary Distribution Unblocking

## Authority and boundary

Owner-authorized from `main@e0bd5589618192b586f65bb5a83903a8f3f374c3`. The owner's
product goal is a legally distributable Windows `.exe` installer for ordinary users.
This milestone works on the six M10-B distribution blockers, B1 and B6 first.
It keeps the PySide6 / PyInstaller onedir / Inno Setup architecture, publishes
no binary, and grants no legal clearance. `distribution_permitted` stays
`false` in every generated record. No product behaviour changes: `src/` is
unchanged. The packaging change is limited to how two library sets are
collected (see §3).

M9.2–M9.4 remain deferred and the open M9.2-A PR is untouched. The clean-machine
matrix, formal Windows UAT, accessibility acceptance and the owner's optional
30-minute packaged smoke remain **NOT RUN**. Signing / SmartScreen (M10-D L5) is
outside B1–B6 and remains open.

## 1. Blocker dispositions

| ID | Status | Evidence | Remaining work → next responsible action |
| --- | --- | --- | --- |
| B1 | **OPEN — narrowed to the bindings and the delivery route** | All 25 shipped Qt library/plugin binaries match the official Qt 6.11.2 build SBOMs. For QtBase and QtSvg, the SBOM's built commit equals the `.tag` commit in the delivered source archives (§2.1) | (a) PySide6/shiboken6 binding binaries have no producer build record: owner/legal accepts the upstream release source as their Corresponding Source, or rebuilds the bindings (E4 toolchain, §5). (b) Owner confirms the same-page source-hosting route (§4). (c) Engineering checks the 96 translation `.qm` files against the official qttranslations archive |
| B2 | **RESOLVED by removal (verified on the actual build, §3)** | `opengl32sw.dll` is the Qt-published Mesa 11.2.2 software renderer: its content matches the official archive. The Widgets-only UI never creates an OpenGL context, so the build no longer ships it | None while it stays excluded. Re-adding it would need Mesa/LLVM compiled-content attribution |
| B3 | **OPEN — owner decision required** | Two Microsoft DLLs were copied from the build host's `System32`, not from a Visual Studio `VC\Redist` folder. The CPython runtime is a third-party build without a producer record (§2.3) | Owner chooses the Microsoft runtime route and the interpreter producer (§2.3). Installing Build Tools alone is not redistribution clearance |
| B4 | **OPEN — narrowed** | Wheel-embedded CycloneDX SBOMs (safetensors, hf-xet) now enter the legal packet. Crates compiled into the three Rust extensions were recovered from the binaries (§2.4) | Engineering: generate crate notices for tokenizers from its exact `Cargo.lock`; decide whether to drop the unused `hf_xet`; review the PyTorch static-content notices |
| B5 | **OWNER/LEGAL DECISION** | The py3langid 0.4.0 model was trained on Wikipedia, Leipzig, CC100, Tatoeba and Glot corpora. No license specific to the model is stated (§2.5) | Owner/legal decides among the options in §2.5 |
| B6 | **OPEN — root cause found; two replacement modes work** | The M10-B failures were caused by a Qt private-API version tag, not by the mechanism. A separately obtained Qt 6.11.2 set and a coherent 6.11.1 Qt/PySide6/shiboken6 set both pass (§2.2) | Demonstrate a replacement built from modified Qt 6.11.2 sources (E4, §5) — owner installs the toolchain |

## 2. Evidence

### 2.1 Qt binary provenance (B1)

The official Qt 6.11.2 MSVC2022 x64 archives were downloaded with owner approval
and checked against the repository's `.sha1` files: qtbase, qtsvg, qtimageformats
and opengl32sw. They are recorded in
[the provenance manifest](../distribution/qt-binary-provenance.json); none is
committed or redistributed.

- **Content identity.** All 21 Qt binaries that both sources contain are
  content-identical: digests that exclude the checksum, security directory and
  certificate table match. They differ only in their Authenticode signature
  blocks.
- **SBOM identity.** Each Qt archive carries an official SPDX 2.3 build SBOM
  (data license CC0-1.0). The SBOM records each built file's SHA-1 *before*
  signing. The new check in [`compliance.py`](../tools/m10/compliance.py)
  removes the certificate table, security directory and checksum, and compares
  the result. **25 of 25 Qt binaries VERIFIED**. The renderer is the only
  uncovered file
  ([receipt](evidence/m10-e1/qt-provenance-m10b-bundle.json)).
- **Source link.** The QtBase SBOM describes
  `qtbase@ef55f427f2c8b410d34f8a7681020a3000cf6866` and the QtSvg SBOM describes
  `qtsvg@17ca512f903f935282ebeca496aac5d11ba4199a`. These are exactly the `.tag`
  commits inside the delivered `*-everywhere-src-6.11.2.tar.xz` archives. The
  SBOM also records the configure command, MSVC 19.44.35227, CMake 3.30.5 and
  Ninja Multi-Config. The archives contain the `configure` scripts and `coin/`
  CI instructions. The QtImageFormats SBOM names the release version but no
  commit (`VERSION_ONLY`).
- **Effect.** For the Qt libraries, the shipped object code is identified with
  its exact source, configuration and toolchain. This is the main gap B1 named.
  The binding layer (PySide6/shiboken6 `.pyd`/`.dll`) has no SBOM or embedded
  commit; it is identified only by its 6.11.2 release.

From now on, the build stages the three SBOMs into `legal/qt-sbom/` (hash-pinned)
and runs this check. Its result goes into `inventory.json` as
`qt_binary_provenance`, and the B1 blocker text narrows only when every Qt
binary verifies and every module links to its delivered archive, by commit or,
where the SBOM names none, by matching release version. After review, the
check also hashes unsigned images unchanged and rejects ambiguous SBOMs and
version mismatches. The narrowed B1 text now states that QtImageFormats is
linked by version only. The committed build receipt keeps the `2a374e2`
artifact's original wording.

### 2.2 Replacement mechanism (B6)

[Replacement evidence](evidence/m10-e1/replacement-evidence.json) records every
changed file hash and outcome. Each experiment ran on a fresh copy of the M10-B
verified bundle (`c93191e`) on the Windows development host.

- **Root cause of the M10-B failures.** Every import from `qt6*.dll` was compared
  with the full export-name table of the bundled Qt DLLs.
  - Original bundle: 0 unresolved imports.
  - 6.11.1 and 6.12.0 Qt-only swaps: `QtCore.pyd` imports
    `??0QObjectPrivate@@QEAA@W4QtPrivate_6_11_2@@@Z`. That is a private-API
    constructor whose parameter type is tagged with the exact Qt version. Other
    Qt versions export only their own tag, so Windows refuses to load the
    bindings (exit 2).
  - This is deliberate Qt version locking for private API. It does not show that
    the shared-library mechanism is incompatible.
- **E3 — separately obtained Qt 6.11.2 libraries: PASS.** 26 Qt DLL and plugin
  files were replaced with the official Qt-signed archive files.
  `--license-info`, `--verify-runtime` and `--smoke` all exited 0, and no
  imports were unresolved. Limitation: the compiled code is the same as the
  wheel's, so this shows file-level replacement, not a modified build.
- **E2 — coherent 6.11.1 Qt + PySide6 + shiboken6 set: PASS.** 43 native files
  were replaced from the upstream 6.11.1 wheels, with no missing counterparts.
  `--license-info` reported Qt **6.11.1**. The runtime check and smoke passed,
  and no imports were unresolved.
- **Structural change.** Until now, the PySide6/shiboken6 *Python* layer was
  frozen inside the PYZ. The spec now collects it as loose files next to its
  DLLs, so the whole LGPL set can be replaced without rebuilding (§3).
- **Not yet shown:** a library built from *modified* 6.11.2 sources. That needs
  an MSVC toolchain, which the host does not have; see E4 in §5. **B6 stays
  OPEN** until E4 passes.

### 2.3 Microsoft runtime and CPython (B3)

Observed origins of the runtime DLLs in the frozen bundle:

| Files | Version | Signer | Origin |
| --- | --- | --- | --- |
| `_internal/msvcp140.dll`, `MSVCP140_ATOMIC_WAIT.dll` | 14.50.35719 | Microsoft Windows | **Byte-identical to the build host's `C:\Windows\System32`**, collected by PyInstaller dependency resolution |
| `_internal/vcruntime140.dll`, `vcruntime140_1.dll` | 14.44.35211 | Microsoft | Copied from the build interpreter's home |
| `PySide6/` and `shiboken6/` `MSVCP140*.dll`, `VCRUNTIME140*.dll` | 14.44.35211 | The Qt Company | Shipped inside the Qt wheels |
| `numpy.libs/msvcp140-*.dll` | 14.40.33810 | Microsoft | Shipped inside the NumPy wheel |
| `python312.dll` and CPython runtime | 3.12.14 | OpenAI OpCo | A tool-bundled CPython build (`main` branch build string), not a python.org release |

What Microsoft states
([redistributing files](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170),
[DLLs to redistribute](https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute?view=msvc-170),
[REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)):

- Redistribution is limited to licensed Visual Studio users.
- Files may come from the `VC\redist` folder of a licensed installation.
- App-local deployment is possible but not recommended.
- `vc_redist.x64.exe` is the recommended route.

No statement covers copying files from `System32`. The licence terms pages
could not be read as text, so this record does not paraphrase their
Distributable Code clauses.

Narrowest owner decisions:

1. **Microsoft runtime route**, one of:
   - **R1:** the installer requires or launches the official
     `vc_redist.x64.exe` obtained from Microsoft at install time, and the bundle
     drops its own copies;
   - **R2:** the owner, as a licensed Visual Studio user, ships app-local copies
     taken only from that installation's `VC\Redist\MSVC\v14x`, and the build
     rejects any `System32` copy.

   Either way, the `System32` copies must not ship.
2. **Interpreter producer:** build the bundle with a CPython whose producer
   publishes the build. That is a python.org Windows release (the last 3.12
   binary, or a supported 3.13 release, which CI already tests), or a published
   standalone-build release. The OpenAI-signed tool runtime should not be used.

### 2.4 Static native content (B4)

[Compiled-crate evidence](evidence/m10-e1/rust-compiled-crates.json) lists the
crate@version pairs recovered from the registry source paths embedded in each
Rust extension. This is a lower bound.

| Extension | Crates found | Upstream SBOM |
| --- | --- | --- |
| tokenizers | 38, including C components `onig` and `esaxx-rs` | none |
| safetensors | 7 | CycloneDX, now preserved |
| hf-xet | 73, including `aws-lc-sys` | CycloneDX, now preserved |

The app downloads models with its own `urllib` client and loads them from
local folders. `hf_xet` is therefore not on any product path, but removing it
needs its own verification. PyTorch ships upstream `third_party` licence files,
which are already preserved (a source superset). NumPy/OpenBLAS and Intel/LLVM
OpenMP remain package-level.

### 2.5 py3langid model (B5)

The installed package is BSD-3-Clause (fork) over BSD-2-Clause (original), with
no separate model licence. Its
[v0.4.0 TRAINING.md](https://github.com/adbar/py3langid/blob/v0.4.0/TRAINING.md)
lists these corpus domains:

- Wikipedia cirrus dumps
- Leipzig Corpora (news)
- CC100 (CommonCrawl 2018)
- Tatoeba sentences (CC BY)
- GlotCC-V1, Glot500 and GlotSparse top-ups

Per-corpus terms are not stated there and were not verified here. Whether
terms on the training text attach to a statistical n-gram model is a legal
question.

Options for the owner:

- accept the model with attribution. Attribution satisfies the BSD notice
  terms only; it does **not** by itself establish a right to redistribute a
  model derived from those corpora. That remains the owner/legal question;
- retrain with the deterministic `py3langid.train` pipeline on corpora with
  verified permissive terms;
- replace the component.

## 3. Packaging change and new build

[`sti_desktop.spec`](../tools/m10/sti_desktop.spec) now sets
`module_collection_mode={"PySide6": "py", "shiboken6": "py"}` and drops
`opengl32sw.dll` from both analyses. [`compliance.py`](../tools/m10/compliance.py)
stages the Qt SBOMs, verifies Qt binaries, preserves wheel `sboms/`, and derives
the B1/B2 text from evidence (B3–B5 unchanged).

An actual Windows x64 build was made with the pinned build manifest at
implementation commit `2a374e2e4539aec6f6f5727d86e056bcb5a786a4`
([receipt](evidence/m10-e1/e1-build-receipt.json)):

- **Layout:** 5,269 files / 745,543,213 bytes; model weights are not bundled.
- **Contents:** 6,646 PYZ modules, none of them PySide6/shiboken6; 102 native
  binaries; `opengl32sw.dll` absent.
- **Qt provenance:** 25/25 Qt binaries VERIFIED. The source links are
  COMMIT_MATCH for qtbase and qtsvg and VERSION_ONLY for qtimageformats.
- **Packet:** both wheel SBOMs preserved; materials valid; four blockers
  (B1 narrowed, B3–B5); `distribution_permitted: false`.
- **Packet regression (found and fixed before merge):**
  - The packet built with `2a374e2` audited **34** components instead of
    36: `PySide6_Essentials` and `shiboken6` and their installed notices
    were missing. The loose-file collection leaves them no PYZ entry, and
    owner discovery read PYZ names only.
  - Tool commit `6ae5fdf` adds owners of loose Python sources shipped
    under `_internal` and records them as `loose_python_packages`.
    Unregistered loose files still become unmapped-owner blockers.
  - On a fresh copy of the same `2a374e2` bundle, the regenerated packet
    audits **36** components. Both bindings are version-matched (6.11.2)
    with their installed notices, and no ownership blockers remain
    ([receipt](evidence/m10-e1/e1-packet-correction-receipt.json)).
  - Executables are byte-identical. `--verify`, `--license-info`,
    `--verify-runtime` and `--smoke` pass. The replacement mechanism and
    every gate are unchanged.
  - The earlier [build receipt](evidence/m10-e1/e1-build-receipt.json)
    describes the original, uncorrected packet.

Frozen checks on that bundle:

- `--license-info`, `--verify-runtime` and `--smoke` exit 0 (native Windows Qt
  window).
- The opt-in frozen pytest pair: **2 passed**.
- DLL closure proxy: 102 binaries scanned, none unresolved.
- Qt import gaps: 0.

Replacement on this bundle:

- **E3b**, 25 official Qt 6.11.2 files: PASS.
- **E2b**, a coherent 6.11.1 set of 44 files including the loose
  `PySide6/__init__.py` and `shiboken6/__init__.py`: PASS, and Qt reports
  6.11.1.

Removing the renderer did not affect any of these Widgets checks.

The M10-C compiled installer is historical: it wraps the M10-B bundle and was
**not** rebuilt with the M10-E1 bundle or packet. Any new installer must be
rebuilt from an M10-E1-or-later bundle and revalidated.

`QT_REPLACEMENT.md` and `SOURCE_ACCESS.md` were rewritten after this build.
That is a text-only change to the legal packet. The receipt describes the
`2a374e2` artifact; it does not relabel that artifact as a build of a later
commit.

## 4. Applicable LGPL route (engineering analysis, not legal advice)

This is the route the evidence supports, against the LGPL v3 and GPL v3 texts
shipped in `legal/`:

- **Combined Work, LGPL v3 §4.** (a) and (b): the Qt notice and both licence
  texts are shipped. (c): a licence dialog is shown. (d)(1): a "suitable shared
  library mechanism" — Qt, PySide6 and shiboken6 are separate run-time-loaded
  files, now including the binding Python layer. §2.2 shows replacement with
  separately obtained and coherent-set libraries. Operation with a *modified*
  interface-compatible version — which §4(d)(1) requires — is not yet shown;
  that is E4 (§5).
  (e): Installation Information applies only where GPL v3 §6 requires it, which
  is for "User Products". Whether a downloadable desktop application falls
  under that is for owner/legal confirmation.
- **The library's own object code, GPL v3 §6.** For a download, §6(d) allows
  offering the Corresponding Source "in the same way through the same place".
  The lowest-cost practice is to attach the five hash-pinned source archives
  and the build SBOMs to the same release page as the installer, and to keep
  `SOURCE_ACCESS.md` pointing there. This is proposed, not active; nothing is
  published.

## 5. E4 — modified-source Qt replacement (defined follow-up)

- **Prerequisite (owner):** install Visual Studio 2022 Build Tools with the
  MSVC v143 14.44 toolset (the SBOM compiler is 19.44.35227) and a Windows 11
  SDK, and accept the Microsoft licence. Installing it does not clear B3.
- **Toolchain:** CMake ≥ 3.30.5 and Ninja (both are available on the host),
  plus the existing Python 3.12.
- **Source:** the pinned `qtbase-everywhere-src-6.11.2.tar.xz`, SHA-256
  `5b2e00ec…cf22`, in a disposable workspace.
- **Modification:** a single visible marker string appended in
  `src/corelib/global/qlibraryinfo.cpp` (the `QLibraryInfo::build()` text).
- **Configure:** follow the SBOM's recorded command, release only, with
  `-qt-zlib` and the same feature set. Build only Core, Gui and Widgets plus
  the platform/style plugins.
- **Validation criteria, all required:**
  1. the rebuilt `Qt6Core.dll` differs from the SBOM hash and contains the
     marker;
  2. 0 unresolved imports against the bundle;
  3. `sti-check.exe --license-info`, `--verify-runtime` and `--smoke` exit 0 on
     a fresh bundle copy with the rebuilt DLLs;
  4. the opt-in frozen pytest pair passes.
- **Expected owner involvement:** the toolchain install and licence acceptance.
  The roughly 1–2 hour build and the validation are engineering work. No
  publication.

## 6. Validation

- **Actual Windows build and frozen checks:** see §3, at implementation
  `2a374e2`.
- **Replacement experiments:** E3, E2, E3b and E2b PASS. The two retained
  M10-B Qt-only experiments are FAIL, with the cause now explained.
  Modified-source E4 is NOT RUN.
- **Local Windows full application suite** (worktree source on `PYTHONPATH`),
  after the review fixes: **1,203 passed / 6 opt-in skipped**.
- **New regressions:** `tests/tools/test_m10_provenance.py` uses synthetic PE
  images, SBOMs and archives. It covers pre-signing digests, rejection of
  malformed or trailing data, VERIFIED / MISMATCH / SOURCE_MISMATCH /
  VERSION_ONLY / VERSION_MISMATCH / NO_SOURCE_ARCHIVE results, PE32 and
  PE32+ images, unsigned images with a checksum, ambiguous SBOMs, an empty
  bundle, uncovered-binary reporting, evidence-derived blockers,
  and the spec and manifest guards.
- **Static checks:** Ruff and strict MyPy (241 files) pass.
- **CI scope:** Linux CI runs the regressions and static checks; it is not
  Windows packaging or replacement evidence.
- **Independent Spec and Standards reviews:** run on the branch.
  - Standards found two real defects, both fixed test-first: unsigned images
    had their checksum zeroed, and VERSION_ONLY modules were never compared to
    the archive version. It also found vacuous test assertions, now fixed.
  - Spec found the B1 text overclaiming commit links for QtImageFormats, the
    §4(d)(1) wording, and four stale statements (the M10-C record, the
    installer notice and the M10-D dossier pointer). All are fixed.
  - Spec's one-second-after-merge audit of the changed current-state
    statements: **100% YES**.
  - The real bundle still verifies 25/25 under the stricter check.
- **Privacy:** evidence files hold relative bundle paths, hashes and public
  upstream URLs only. Downloaded archives, extracted official binaries, built
  bundles and logs stay local under ignored `_local/`.
