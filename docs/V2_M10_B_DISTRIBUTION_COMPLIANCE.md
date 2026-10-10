# M10-B — Qt LGPL and Third-Party Distribution Compliance

## Authority and boundary

Owner-authorized from `main@282597b9f2c04742ba44bbb702b8ce352f7d0bfa`.
The M7/M10-A Windows x64 PyInstaller onedir architecture and dependencies are
retained. This work adds licensing materials, inventory validation and a visible
Qt license entry; it adds no product capability, installer or distribution.
The legal/distribution gate remains **BLOCKED**, not legally certified.

M9.0 remains historical owner-approved design, M9.1 COMPLETE and merged,
M9.2–M9.4 DEFERRED. Q5 evidence restrictions, M7 CONDITIONAL and all unresolved
M7/M8 risks remain. The optional owner **30-minute packaged smoke is NOT RUN**;
bounded automated smoke and DLL compatibility are not human Windows UAT,
accessibility acceptance, model evaluation or V2 release readiness.

## Audit basis and delivered materials

The audit reads both frozen PYZ tables and actual onedir files rather than
equating application imports with distributed contents. The previous M10-A
artifact establishes the starting footprint; every new build rechecks it.
`distribution/component-register.json` records 35 observed Python package
owners and one PyInstaller bootloader component (36 entries total), exact
versions, selected license expressions and public upstream evidence. The project
itself is identified by source SHA and repository version, not stale editable
installation metadata. The `py` shim is owned by pytest 8.4.2 even though the
pytest runner is excluded; this included fragment is inventoried honestly.
PyInstaller's `_pyi_rth_utils` is resolved from its installed fake-module header;
its Apache-2.0 attribution is separate from the bootloader's GPL exception.

The build assembles `legal/inventory.json` containing module names, package
notice receipts, native file ownership, hashes of delivered files, source
archive hashes, provenance and unresolved obligations. Full package license
files and nested vendored notices are preserved; no private installation paths,
raw environment records or editable `direct_url.json` are copied by this tool.
Structural verification detects missing/changed delivered bytes. It does not
set `distribution_permitted` to true, even when all structural checks pass.

Qt 6.11.2/PySide6-Essentials/shiboken6 use the LGPL v3 route; the installed binding
wheels contain only a commercial-license reference, so that reference is not
accepted as an LGPL grant or a complete notice packet. Full LGPL v3 and GPL v3
texts come from the independently hash-checked QtBase 6.11.2 source archive.
`qt-notices/` preserves license/copyright/attribution entries from the accompanying
sources. Its scope is an upstream source superset, **not** a compiled-content
SBOM. Qt Network/Svg, image plugins, translations and `opengl32sw.dll` remain
within the audit despite the application importing only Core/Gui/Widgets.

The five source archives and their official checksum receipts are versioned in
[the source manifest](../distribution/source-manifest.json). Actual archives stay
local and accompany the local engineering artifact. This source-delivery
mechanism is concrete but incomplete as an exact-binary corresponding-source
claim; it is not an unsupported three-year written offer. User-facing
[source access](../distribution/legal/SOURCE_ACCESS.md) and
[replacement/install instructions](../distribution/legal/QT_REPLACEMENT.md)
describe the route and its unresolved build details.

## Obligations and blockers

| ID | Evidence / required closure | Status |
| --- | --- | --- |
| B1 | Upstream release archives delivered; exact Qt/PySide wheel patches, flags, corresponding source and producer build recipes still need verification and delivery | OPEN, blocks distribution |
| B2 | `opengl32sw.dll` software renderer provenance and compiled Mesa/LLVM attribution cannot be inferred from Qt version | OPEN, blocks distribution |
| B3 | Microsoft runtime redistribution grant and custom CPython/native runtime producer provenance/build details must be established; installed/public binaries do not imply permission | OPEN, blocks distribution |
| B4 | Rust/static native dependencies and vendored components require compiled-content/license coverage; package-level labels and source-superset notices are insufficient | OPEN, blocks distribution |
| B5 | py3langid's embedded model training-corpus redistribution terms remain the pre-existing risk | OPEN, blocks distribution |
| B6 | Both tested Qt-only DLL/plugin replacements failed with unchanged 6.11.2 bindings; a coherent compatible replacement or rebuild must be demonstrated | OPEN, blocks distribution |

MIT/BSD portions require preserved copyright/license and applicable disclaimer
or non-endorsement statements. Apache portions require license and applicable
NOTICE/attribution handling. MPL portions (including certifi) require the
applicable covered-source access and notice obligations; exact shipped source
and modifications must be checked. The PyInstaller bootloader exception is
considered under its actual installed COPYING text, not a blanket GPL waiver.
No GPL-only application Qt module is imported; this is not a substitute for
identifying all statically embedded code. Additional unknown ownership or absent
notices are recorded by the generated inventory and block any clearance.

## Authoritative references

- [Qt 6.11 licensing](https://doc.qt.io/qt-6.11/licensing.html)
- [Versioned LGPL v3 terms](https://doc.qt.io/qt-6.11/lgpl.html): prominent notice, both GNU texts, modification/reverse-engineering rights, compatible shared-library operation and conditional installation information
- [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
- [Qt 6.11.2 third-party license list](https://doc.qt.io/qt-6.11/licenses-used-in-qt.html): actual compiled components, not every source entry
- [Qt for Python terms](https://doc.qt.io/qtforpython-6.11/index.html)
- [Python license history](https://docs.python.org/3.12/license.html), supplemented by the actual Python 3.12.14 runtime LICENSE.txt
- [Python 3.12.14 release](https://www.python.org/downloads/release/python-31214/)
- [PyInstaller license and exception](https://pyinstaller.org/en/stable/license.html), supplemented by installed 6.22.3 COPYING.txt
- [Microsoft runtime redistribution requirements](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)
- [Tokenizers 0.22.2 full license](https://github.com/huggingface/tokenizers/blob/v0.22.2/LICENSE) and [OpenSSL 3.5.8 license](https://github.com/openssl/openssl/blob/openssl-3.5.8/LICENSE.txt), supplied separately where installed materials are insufficient

## Verification record

### Actual Windows artifact and material validation

The actual Windows x64 PyInstaller freeze completed on application/binary input
SHA `c93191ee4d0677f7e78a99fca8b89460b503e7f5`. Its first material stage failed:
the deliberately isolated build PATH contains no Git, while the assembler
attempted an internal Git lookup. The driver now passes its already-verified
application SHA; the PATH isolation is retained. A later audit identified and
attributed the included PyInstaller Apache runtime helper.

The final material tool SHA is `e6fdd85abd7c36cf368a871fd7f5a323e20670d2`.
The committed diff confirms all binary inputs (application, spec, entry files,
build requirements and embedded project notices) are unchanged from `c93191e`.
The preserved `_internal` tree and two executables were copied to a fresh folder;
material assembly and verification then passed under the same Git-free PATH.
Executable byte equality was checked. This is a successful resumed material
stage over an actual frozen build, **not** a claim that the original complete
build-driver invocation succeeded. All failed outputs remain local.

The final folder has **5,265 files / 761,696,609 bytes**, unbundled model weights,
**6,648 PYZ modules**, **36 registered components**, and **103 native binaries**
(DLL/PYD/EXE). The full local inventory is 1,513,576 bytes, SHA-256
`896f53e8337b5208bd714df369f8eb07a9471c69c2f202cf172921083efda607`.
Its 5,264 material receipts deliberately exclude only the inventory itself.
The 224 source-notice entries occupy 190 unique hash-named files; their scope
remains a source superset. Five complete, hash-verified release archives
accompany the engineering artifact. All delivered-byte/set checks pass;
`distribution_permitted` remains false. The generated inventory records B1–B5;
B6 is retained separately in the actual compatibility evidence.

[The sanitized inventory receipt](evidence/m10-b/inventory-receipt.json) records
component versions, selected terms, original notice paths/hashes, native paths
and hashes, source receipts and artifact identity. No binaries, private build
logs, machine paths or source archives are published in this PR.

### Actual Windows replacement experiments

Two independent PyPI upstream wheels were downloaded and hash-checked without
installing them: PySide6-Essentials **6.11.1** and **6.12.0**. Each experiment used
a separate fresh copy of the original bundle, replacing five Qt DLLs and 20
matching plugin DLLs while retaining the original 6.11.2 Python bindings and
executable bytes. In both cases `--license-info` exited **2**; no replacement Qt
version was verified. Subsequent runtime/smoke checks on those copies are
**NOT RUN**, not passing. The exact ABI/loader cause is not established.
The original bundle still reports Qt **6.11.2** and both original frozen runtime
and synthetic native-smoke regressions pass (**2 passed**).

[Replacement evidence](evidence/m10-b/replacement-evidence.json) preserves both
wheel receipts, all 25 changed-file hashes per experiment and failed outcomes.
Neither a compatible arbitrary library rebuild nor successful relinking has
been demonstrated; **B6 remains OPEN**. The user-facing replacement procedure
requires a coherent compatible library/wrapper set where necessary and does
not represent these failed experiments as a validated installation recipe.

### Regression and review evidence

- Windows full application suite on `c93191e`: **1,176 passed / 6 skipped**
  (four opt-in model/network tests and two opt-in frozen checks). Later commits
  modify only the material tooling/attribution and focused regressions; product
  sources are unchanged.
- Final focused material/build checks: **15 passed**; lifecycle and real Qt
  notice checks: **8 passed**; actual original frozen checks: **2 passed**.
- Ruff, strict MyPy (**239 files**), compileall and dependency consistency pass.
- [Fresh implementation-head CI](https://github.com/Peter-S-Shi/social-text-intelligence/actions/runs/38096001797)
  on `e6fdd85`: Python 3.11/3.12/3.13 each **1,176 passed / 8 skipped**, quality
  checks pass; Node **12 passed**. Linux CI is not Windows replacement evidence.
- Independent Spec and Standards reviews cover implementation and final actual
  governance/evidence: **both PASS, no unresolved review findings**. Both audited
  every changed current-state statement with the one-second-after-merge test:
  **100% YES**. Engineering review does not clear B1–B6 or imply owner
  acceptance. Final closeout is documentation/evidence-only `[skip ci]`.

[Windows screenshots](../manual-qa/m10-b-visual-evidence/README.md) show the
prominent license entry at 1280px and 900px and its full dialog. They are source
Qt captures of synthetic/disposable state, not frozen UI screenshots, formal
Windows UAT or accessibility acceptance. M6/M8 evidence is unchanged.
