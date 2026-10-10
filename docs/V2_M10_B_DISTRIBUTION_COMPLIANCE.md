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
`distribution/component-register.json` records the 36 observed Python package
owners plus bootloader (36 entries total, because one is PyInstaller), exact
versions, selected license expressions and public upstream evidence. The project
itself is identified by source SHA and repository version, not stale editable
installation metadata. The `py` shim is owned by pytest 8.4.2 even though the
pytest runner is excluded; this included fragment is inventoried honestly.

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

Actual frozen-build and replacement observations are recorded in the final
validation closeout. Linux CI tests infrastructure and regressions only; it
cannot establish Windows DLL compatibility or legal compliance.
