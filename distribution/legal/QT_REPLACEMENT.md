# Replacing the dynamically linked Qt libraries on Windows

Qt, PySide6 and shiboken6 are separate files in `_internal/PySide6/` and
`_internal/shiboken6/`; the application loads them at run time. There is no
signature check, executable patch or replacement lock.

## Which replacement works

The PySide6 6.11.2 binding binaries import Qt private API that Qt tags with its
exact version (for example the import
`??0QObjectPrivate@@QEAA@W4QtPrivate_6_11_2@@@Z` in `QtCore.pyd`). Therefore:

- **Qt libraries only:** the replacement must be an interface-compatible Qt
  **6.11.2** build, for example your own build of the delivered 6.11.2 sources,
  with or without modifications. Qt 6.11.1 or 6.12.0 libraries alone cannot
  satisfy that versioned import, so Windows refuses to load the bindings.
- **Coherent set:** to use another Qt version, replace Qt **together with** the
  matching PySide6 and shiboken6 files of that same version (binaries and the
  loose Python files).

## Procedure

1. Close all STI processes. Make a separate copy of the entire `sti-desktop`
   onedir folder and work only in the copy. Do not use real project data.
2. Obtain the replacement files and check their provenance and hashes:
   - Qt-only: Windows x64 MSVC Qt 6.11.2 shared libraries and plugins.
   - Coherent set: a PySide6-Essentials wheel and the shiboken6 wheel of one
     version. A wheel is a ZIP archive; its `PySide6/` and `shiboken6/` folders
     hold the files.
3. Overwrite each existing file in the copied `_internal/PySide6/` (and, for a
   coherent set, `_internal/shiboken6/`) with the file of the same relative path
   from the replacement. Keep the layout, and replace a plugin only together
   with the Qt build it belongs to.
4. In the copy, run `sti-check.exe --license-info`, then
   `sti-check.exe --verify-runtime` and `sti-check.exe --smoke`. The first
   reports the Qt version actually loaded; the last creates and removes
   disposable synthetic app data. A crash or non-zero exit is a failed
   replacement, not acceptance.
5. Optionally open the copied `sti-desktop.exe` and use the footer's
   **Licenses · Qt LGPL** button. To undo, discard only the copy you created.

## What has been observed

The [M10-E1 record](../../docs/V2_M10_E1_DISTRIBUTION_UNBLOCKING.md) has the
exact results. On a Windows x64 development host: the officially distributed
Qt 6.11.2 binaries, downloaded separately and Qt-signed, and a coherent
6.11.1 Qt/PySide6/shiboken6 set each passed all three checks. A Qt-only 6.11.1
or 6.12.0 swap fails for the versioned-import reason above.

A replacement built from **modified source** has been demonstrated for
**QtCore only** (M10 S3):
- `Qt6Core.dll` was rebuilt from the delivered 6.11.2 source with one visible
  change, using MSVC 19.44. It replaced the shipped file in a copy of the
  application.
- The copy passed all three checks and the opt-in frozen tests, with no
  unresolved Qt imports. The rebuilt library is unsigned and is accepted.
- A modified-source rebuild of Gui, Widgets or the plugins has **not** been
  demonstrated. The running application's reported build string was not
  captured. No compatibility with
arbitrary changes, future versions, formal Windows UAT or legal compliance is
implied. Reverse engineering to debug modifications of these libraries is
permitted; no contractual term prohibits it.
