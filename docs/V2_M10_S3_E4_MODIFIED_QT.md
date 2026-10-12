# V2 M10 S3 — B6: E4 modified-source QtCore replacement

Status: **S3 COMPLETE on `main` (PR #66). E4 PASSES on the narrower M10-E2
§2.6 criterion: QtCore only.** B6 is recorded as **CLOSED on that criterion**,
which the owner accepts by merging this PR. The original M10-E1 §5 scope also
rebuilt Gui, Widgets and the plugins from modified source. That part was **not
exercised** (§4). This is not a full modified-source rebuild of every Qt
component.

Binary distribution remains **BLOCKED** on B1, B4 and the clean-machine matrix
(S5), and `distribution_permitted` stays false. This is evidence only: no product,
packaging or compliance code changed, and nothing was published.

## 1. Prerequisites

| Item | Found |
| --- | --- |
| Toolchain (installed and licence-accepted by the owner) | Visual Studio Build Tools 2022 17.14, MSVC toolset 14.44.35207, `cl` **19.44.35229** x64. The Qt 6.11.2 SBOM records 19.44.35227, from the same 14.44 toolset family |
| Windows SDK | 10.0.26100.0 (`rc.exe` on PATH under vcvars64) |
| CMake / Ninja | 3.31.6-msvc6 / 1.12.1, both bundled with Visual Studio |
| Qt source | `qtbase-everywhere-src-6.11.2.tar.xz`, SHA-256 equals the pin `5b2e00ec…cf22` |
| Frozen bundle | the M10 S2 build at `fbb6e13`, which differs from `main@a2db4bd` only in documentation; original `Qt6Core.dll` SHA-256 `d6a3c37c…c653` |
| `e4_modified_qt.ps1 -CheckOnly` | exit 0, "E4 prerequisites present." |

A MinGW toolchain directory was on the user PATH, ahead of Visual Studio's CMake
and Ninja. For the run it was removed from PATH, so CMake identified only MSVC
19.44.35229. The script itself was not changed.

## 2. Run

`tools/m10/e4_modified_qt.ps1` was run unchanged from `a2db4bd`:

1. It unpacked the pinned qtbase source and applied the single patch in
   `qt_build_string()`: `" build; by "` became `" build, STI-E4-MODIFIED; by "`.
2. It configured Qt with
   `-release -force-debug-info -nomake examples -nomake tests -qt-zlib -- -DFEATURE_msvc_obj_debug_info=ON`
   (RelWithDebInfo, Ninja) and built only the `Core` target: 413 steps, no
   errors.
3. It copied the bundle and replaced only `_internal/PySide6/Qt6Core.dll`.

Afterwards, the existing opt-in frozen tests were run against that modified copy
without rebuilding.

## 3. Results

| Check | Result |
| --- | --- |
| Rebuilt `Qt6Core.dll` | SHA-256 `64359b5c…11ac5`, 10,352,128 bytes; differs from the shipped, SBOM-verified file; the marker occurs once (none in the original) |
| Copy versus original | 5,360 files each; only `_internal/PySide6/Qt6Core.dll` differs |
| Original bundle afterwards | `Qt6Core.dll` unchanged (`d6a3c37c…c653`) |
| Unresolved Qt imports (`e4_check.py`) | **0** |
| `--license-info` | exit 0; `qt_version` 6.11.2; `distribution_permitted: false` |
| `--verify-runtime` | exit 0; `ready: true` |
| `--smoke` | exit 0; window shown, project imported (2 rows, 1 invalid), reopened |
| Opt-in frozen pytest (`STI_M10_BUNDLE` set to the modified copy) | **2 passed** (`--verify-runtime`, `--smoke`) |
| Script verdict | `E4 PASS`, exit 0 |

Evidence: [e4-receipt.json](evidence/m10-s3/e4-receipt.json).

**Unverified.** The runtime `QLibraryInfo::build()` string was not captured, so
it is **unverified** that the running app reports the marker. That the copy loads
its own `_internal/PySide6/Qt6Core.dll` is inferred from the self-contained
onedir layout and the passing checks, not observed. The rebuilt library is
unsigned, while the shipped one is Qt-signed. That is expected for a user's own
rebuild.

## 4. Scope reconciliation (M10-E1 §5 against M10-E2 §2.6)

| M10-E1 §5 item | This run |
| --- | --- |
| Pinned qtbase source, one visible marker in `qlibraryinfo.cpp` | done |
| Configure as the SBOM records, release, `-qt-zlib` | done |
| Rebuild **Core** | done |
| Rebuild **Gui** and **Widgets** | **not exercised**: the shipped Qt-signed files remain |
| Rebuild the **platform and style plugins** | **not exercised**: the shipped files remain |
| Criterion 1: the rebuilt `Qt6Core.dll` differs from the SBOM file and has the marker | met |
| Criterion 2: 0 unresolved imports | met |
| Criterion 3: the three frozen checks exit 0 on a fresh copy | met |
| Criterion 4: the opt-in frozen pytest pair passes | met (2 passed) |

**What this shows.**
- A QtCore built by a third party from the delivered, modified source, with an
  interface-compatible version, toolset and configuration, can replace the
  shipped QtCore. The application then loads, starts its window and completes the
  smoke workflow.
- Every Qt import is still satisfied with the shipped Gui, Widgets, plugins and
  bindings.

**How it relates to the earlier evidence.** M10-E2 §2.6
([replacement-e2c.json](evidence/m10-e2/replacement-e2c.json)) replaced all 36
PySide6/shiboken6/Qt files coherently with the separately obtained upstream
6.11.1 wheels, and passed. That covers replacing every Qt module, including Gui,
Widgets and the plugins, but with unmodified upstream binaries.

Together, the two runs show:
- whole-set replacement with unmodified upstream binaries;
- modified-source replacement for QtCore.

They do **not** show a modified-source rebuild of Gui, Widgets or the plugins.

## 5. Still open

- **B1** stays OPEN: the binding binaries' Corresponding Source and the source
  route need an owner/legal position (S4).
- **B4** stays OPEN: Intel OpenMP redistribution is not approved.
- **B5:** the corpus terms stay unverified, and the core installer does not ship
  the model.
- **S5** (clean-machine matrix) is NOT RUN.
- **Left for the later packaging/compliance integration milestone:**
  `tools/m10/installer.py` still writes a fixed `legal_blockers` list (B1–B6)
  into the installer receipt.
- R1 is unchanged, and R2 stays parked in draft PR #62.
