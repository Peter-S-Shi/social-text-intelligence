# V2 M10 S3 — B6: E4 modified-source QtCore replacement

Status: **S3 COMPLETE on `main` (PR #66). E4 PASS, so B6 is CLOSED** on the
criterion recorded in M10-E1 §5 and M10-E2 §2.6: a QtCore rebuilt from the
delivered source with a visible modification must replace the shipped one in a
copy of the frozen bundle, and the established frozen checks must pass.

Binary distribution remains **BLOCKED** on B1, B4 and the clean-machine matrix
(S5), and `distribution_permitted` stays false. This is evidence only: no product,
packaging or compliance code changed, and nothing was published.

## 1. Prerequisites

| Item | Found |
| --- | --- |
| Toolchain (installed and licence-accepted by the owner) | Visual Studio Build Tools 2022 17.14, MSVC toolset 14.44.35207, `cl` **19.44.35229** x64 |
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
   (RelWithDebInfo, Ninja) and built the `Core` target: 413 steps, no errors.
3. It copied the bundle and replaced only `_internal/PySide6/Qt6Core.dll`.

## 3. Results

| Check | Result |
| --- | --- |
| Rebuilt `Qt6Core.dll` | SHA-256 `64359b5c…11ac5`, 10,352,128 bytes; the marker occurs once (none in the original) |
| Copy versus original | 5,360 files each; only `_internal/PySide6/Qt6Core.dll` differs |
| Original bundle afterwards | `Qt6Core.dll` unchanged (`d6a3c37c…c653`) |
| Unresolved Qt imports (`e4_check.py`) | **0** |
| `--license-info` | exit 0; `qt_version` 6.11.2; `distribution_permitted: false` |
| `--verify-runtime` | exit 0; `ready: true` |
| `--smoke` | exit 0; window shown, project imported (2 rows, 1 invalid), reopened |
| Script verdict | `E4 PASS`, exit 0 |

Evidence: [e4-receipt.json](evidence/m10-s3/e4-receipt.json).

**Not shown.** The receipt does not capture `QLibraryInfo::build()` at runtime.
That the copy loads its own `_internal/PySide6/Qt6Core.dll` follows from the
self-contained onedir layout and the passing checks. The rebuilt library is
unsigned, while the shipped one is Qt-signed. That is expected for a user's own
rebuild.

## 4. Scope and what stays open

- **Not changed:** E4 replaces QtCore only, and the PySide6 and shiboken6 binding
  binaries are the shipped ones. That is E4's defined scope. No other Qt module
  was rebuilt, and no rebuild redesign was attempted.
- **B1** stays OPEN: the binding binaries' Corresponding Source and the source
  route need an owner/legal position (S4).
- **B4** stays OPEN: Intel OpenMP redistribution is not approved.
- **B5:** the corpus terms stay unverified, and the core installer does not ship
  the model.
- **S5** (clean-machine matrix) is NOT RUN.
- **Follow-up:** `tools/m10/installer.py` still writes a fixed
  `legal_blockers` list (B1–B6) into the installer receipt. This evidence-only
  milestone leaves the code unchanged.
- R1 is unchanged, and R2 stays parked in draft PR #62.
