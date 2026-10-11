# Replacing the dynamically linked Qt libraries on Windows

1. Close all STI processes. Keep the original local bundle unchanged and make
   a separate copy of the entire `sti-desktop` onedir folder. Do not edit an
   installed user profile or reuse real project data for this experiment.
2. Obtain independently sourced, appropriately licensed Windows x64 Qt shared
   libraries compatible with Qt 6.11 and the PySide6 6.11 ABI. Verify their
   upstream provenance and hashes. A wheel is a possible engineering test
   source, not automatic evidence of full redistribution permission.
3. Replace the Qt DLLs in `_internal/PySide6/` and the matching files under
   `_internal/PySide6/plugins/` with the compatible build. Keep filenames and
   layout. Do not replace only a plugin with one from an incompatible Qt build.
   If modifying wrapper ABI, rebuild and replace PySide/shiboken as a coherent
   set. Keep the Python/runtime architecture compatible. No executable patch
   or executable rebuild is required for an interface-compatible Qt replacement.
4. In the copied folder run `sti-check.exe --license-info`,
   `sti-check.exe --verify-runtime` and `sti-check.exe --smoke`.
   The first reports the Qt version actually loaded; the last creates and
   removes disposable synthetic app data. Use a fresh temporary environment for
   caches and avoid supplying personal projects or model weights. A crash or
   dependency failure is a failed compatibility experiment, not acceptance.
5. Open the copied `sti-desktop.exe` if desired and use the footer's
   **Licenses · Qt LGPL** button. The material-opening action exposes the
   accompanying license texts, source archives and inventory. Restore the
   original copy by discarding only your explicitly created experiment folder.

The M10-B record bounds the tested replacement and its observed outcome.
Compatibility with arbitrary changes, future Qt versions, security policy,
formal Windows UAT and LGPL compliance is not implied. Reverse engineering to
debug LGPL-library modifications is permitted; no contractual prohibition or
technical replacement lock is added.
