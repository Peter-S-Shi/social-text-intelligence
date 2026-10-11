# V2 M10-E3 — App-local Visual C++ runtime (route R2)

Status: **R2 IN PROGRESS — not complete.** The tooling, the measured dependency
closure and the loader analysis are in place. The licence, DLL-loading and
clean-machine tests have not passed, because three owner inputs are still missing
(§6). Binary distribution remains **BLOCKED** and `distribution_permitted` stays
false. Nothing was published or merged.

Baseline: stacked on the M10-E2 branch (PR #61, head `6179aa5`). M10-E2's R1
implementation and its engineering evidence are unchanged: R1 is kept as the
engineering baseline and is still the build default.

## 1. Owner acceptance target

The owner confirmed the final Windows installer acceptance target:

- The system is a supported, normally configured Windows 10/11 x64 machine.
- No VC++ Redistributable is preinstalled, and the user has no administrator rights.
- STI must install and launch without an external prerequisite installer.

R1 does not meet this target. Its installer stops when the system runtime is
absent (M10-E2 §2.2). So R1 is not the release deployment choice. R2 ships the
runtime app-locally from a licensed Visual Studio installation.

## 2. Required runtime closure (measured)

This was measured on the final M10-E2 frozen bundle (`ba2887b`, 87 native files).
It reads every ordinary and delay-load import with the build's own PE parser:

| DLL | Importing binaries |
| --- | --- |
| `vcruntime140.dll` | 83 |
| `msvcp140.dll` | 24 (includes the relinked NumPy import) |
| `vcruntime140_1.dll` | 22 |
| `msvcp140_1.dll` | 4 |
| `msvcp140_2.dll` | 2 |
| `msvcp140_atomic_wait.dll` | 1 (PyTorch) |

- **Executables:** `sti-desktop.exe` and `sti-check.exe` import only Windows system
  DLLs. The PyInstaller bootloader links the CRT statically.
- **Never imported:** `concrt140`, `vccorlib140`, `vcomp140` and the MFC/legacy
  `msvcr*` runtimes.
- **UCRT:** 14 `api-ms-win-crt-*` API sets are imported (335 references). UCRT is
  an operating-system component on Windows 10/11. Microsoft documents that the
  system UCRT is always used there, even when an app-local copy exists. So UCRT is
  not shipped.

These six names are `required_files` in `distribution/vc-runtime.json`. An R2
build stops if any binary imports a Visual C++ runtime DLL outside this set. That
way, a dependency upgrade cannot silently widen the closure.

## 3. Loader locations

The six DLLs are placed in the **application directory**, beside both
executables. That one location satisfies every load path in the bundle:

| Load path | Search behaviour | Application directory searched |
| --- | --- | --- |
| Bootloader loads `_internal/python313.dll` | `LOAD_WITH_ALTERED_SEARCH_PATH`: the DLL's folder, then the standard order | Yes (standard order) |
| CPython loads `.pyd` extensions (PySide6, shiboken6, NumPy, tokenizers, ...) | `LOAD_LIBRARY_SEARCH_DEFAULT_DIRS` plus the DLL's folder | Yes (`LOAD_LIBRARY_SEARCH_APPLICATION_DIR`) |
| Qt plugins and PyTorch's `torch/lib` DLLs | Default directories plus `os.add_dll_directory` folders | Yes |
| `ctypes` by-name loads (PyTorch's runtime probe) | Default directories | Yes |

After the first load, the loader reuses an already-loaded module by name. So each
DLL has exactly one instance in the process.

The application directory is the location Microsoft documents for app-local
deployment. It is searched without relying on any search path that the bootloader
or a package sets up at run time. The per-package copies that the PySide6 and
PyTorch wheels carry are still removed by the spec: they do not come from
`VC\Redist`.

**Probe:** `tools/m10/runtime_origins.ps1` launches `sti-desktop.exe` and lists each
loaded Visual C++ runtime module with its folder. It changes no files and needs no
administrator rights. On the M10-E2 R1 bundle on the development host:

- the window appeared;
- all six DLLs were already loaded at that point, so startup alone covers the whole
  closure, PyTorch included;
- every one came from Windows (`origins_ok: true` for R1).

For R2, the same probe must report `application` for all six (§5, step 3). This
has not been run, because no R2 bundle exists yet.

## 4. Licensing facts read (Microsoft pages, 2026-10-11)

- **Visual Studio 2022 redistribution list** (learn.microsoft.com, the "REDIST.txt"
  that the Community, Professional and Enterprise 2022 licence terms point to):
  - Licensed users may distribute the **unmodified** files under `VC\redist` and
    its subfolders.
  - The `debug_nonredist` folders are excluded.
- **"Redistributing Visual C++ files"** (learn.microsoft.com):
  - Distribution is limited to licensed Visual Studio users.
  - App-local installation into the folder that holds the executable is supported.
  - For servicing reasons, Microsoft does not recommend it.
- **"Deployment in Visual C++"** (learn.microsoft.com):
  - Microsoft cannot update locally deployed copies.
  - The application owner must redeploy them (§5 procedure).
- **Visual Studio Community 2022 licence terms:** not read yet. The page embeds the
  licence as a Word document, `Visual-Studio-2022-Community-License-EN.docx` on
  visualstudio.microsoft.com, which needs a file download. The eligibility rules
  (individual or organization use, and the enterprise thresholds) and the
  "Distributable Code" conditions are therefore **unverified**. They are not
  stated here from memory.
- **Availability:** Microsoft's "older downloads" page (2026-07-13) says older
  versions require an active Visual Studio subscription.
  - That page lists Professional 2022, Enterprise 2022 and Build Tools 2022, but
    not Community 2022.
  - The current free Community edition is Visual Studio 2026 (version 18).
  - Its runtime has its own licence entry: "Microsoft Visual C++ V14
    Redistributable and Runtime 2026".
  - Whether Community 2022 can still be obtained without a subscription is
    unconfirmed (§6).

## 5. Reproducible pinning, packaging and security-update procedure

The procedure is version-pinned at every step. Nothing is downloaded or installed
by the tooling.

1. **Pin.** On the owner's licensed installation, run:
   `python tools/m10/vc_runtime.py --pin --vs-install <VS root>`. It:
   - reads the default redistributable version from
     `VC\Auxiliary\Build\Microsoft.VCRedistVersion.default.txt`;
   - takes the single `VC\Redist\MSVC\<version>\x64\Microsoft.VC1xx.CRT` folder,
     which is never `debug_nonredist`;
   - requires each of the six files to carry a valid Authenticode signature whose
     subject organization is exactly `Microsoft Corporation`;
   - requires each file version to be at least 14.44;
   - records `redist_version`, SHA-256 and file versions in
     `distribution/vc-runtime.json`. The pin is committed and reviewed like any
     packaging input.
2. **Build.** Run
   `python tools/m10/build.py --runtime-route r2 --vs-install <VS root> --output ... --source-dir ...`.
   The build:
   - refuses an installation whose redistributable version differs from the pin;
   - re-checks signatures and hashes;
   - verifies the import closure (§2) and copies the six files unmodified beside
     the executables;
   - accepts no runtime file anywhere else.

   The packet (`legal/inventory.json`, `microsoft_runtime`) records the route, the
   shipped files and the pin match. It derives B3 as open until the owner's licence
   confirmation is recorded in the manifest. `build-evidence.json` records the
   route, the measured imports and the staged receipts.
3. **Probe on the host:** run `tools/m10/runtime_origins.ps1 -Route R2` on the
   frozen bundle. All six modules must load from the application directory, even
   where a system runtime exists.
4. **Installer.** `installer.py` admits runtime files only when the packet says R2
   and they match the pin. It then renders `RequireSystemRuntime = False`. The
   per-user, never-elevating setup (`PrivilegesRequired=lowest`) stays unchanged.
5. **Clean-machine validation:** `validate_installer.ps1 -EnvironmentKind DisposableVM`.
   For an R2 receipt it first asserts:
   - there is no `System32\vcruntime140.dll` and no
     `HKLM\...\VC\Runtimes\x64` key;
   - the user is not an administrator.

   Then it installs, launches, checks module origins, runs the frozen checks,
   uninstalls and reinstalls.
6. **Security updates.** App-local copies receive no Windows Update servicing.
   - For every STI release, and whenever Microsoft publishes a Visual C++ runtime
     security fix (MSRC advisory or Visual Studio release notes), update the
     licensed Visual Studio installation.
   - Then repeat steps 1–5 and ship a new installer.
   - A pin older than the newest serviced redistributable is a release blocker for
     the next release.

## 6. Owner inputs needed before R2 can complete

1. **Licence text download (approval).** Download the Community licence document
   named in §4, a small .docx from visualstudio.microsoft.com, so its eligibility
   and "Distributable Code" conditions can be recorded verbatim. If the owner
   picks Visual Studio 2026, its licence and the 2026 runtime terms are needed
   instead.
2. **Product choice and eligibility (owner confirmation).**
   - Community 2022 appears to be subscription-only now (§4).
   - **Recommendation:** use the current Visual Studio Community 2026 if its terms
     fit the owner's situation. Its runtime is the newest serviced v14 line and is
     binary compatible with the 14.44 minimum.
   - Otherwise, confirm a way to obtain Community 2022 legitimately.
   - Either way, the owner confirms eligibility under the licence actually
     installed. That confirmation is recorded as `owner_licence_confirmation`.
     The tooling never infers it.
3. **Installation (owner action).** The owner installs that edition with the
   "Desktop development with C++" workload and accepts its licence. This same
   installation also provides the MSVC compiler and Windows SDK for the E4 Qt
   rebuild (B6). Installing it is not, by itself, B3 clearance.
4. **Isolated Windows environment (owner action).** This development host runs
   Windows 11 Home, which has neither Windows Sandbox nor Hyper-V. Provide one of:
   - a VirtualBox/VMware VM or a second PC with a fresh Windows 10/11 x64 install;
   - a standard user account;
   - a checked absence of the VC++ runtime;
   - the `C:\STI-M10C-VM.txt` marker required by `validate_installer.ps1`.

## 7. Blocker status (unchanged by this milestone)

| Blocker | Status |
| --- | --- |
| B1 | **OPEN** (as M10-E2) |
| B2 | **CLOSED** (as M10-E2) |
| B3 | **CLOSED for the R1 baseline** (as M10-E2). An R2 build re-derives B3 as open until the pin matches and the owner licence confirmation is recorded |
| B4 | **OPEN** (as M10-E2) |
| B5 | **OPEN — owner/legal decision** (as M10-E2) |
| B6 | **OPEN** (as M10-E2) |

The LGPL gates, the replaceable PySide6 binding layer and every distribution gate
are unchanged.

## 8. Validation in this milestone

- **Unit tests** (`tests/tools`): 110 passed, 2 skipped (frozen-bundle tests need
  an explicit bundle). New tests cover:
  - signer, lookalike-signer, version and byte refusal;
  - pin recording that leaves the confirmation unset;
  - the import-closure guard;
  - app-local placement only beside the executables;
  - R2 B3 derivation;
  - installer prerequisite rendering for R1 and R2.
- **Real signatures:** the signature and version reader was exercised on real
  Microsoft-signed system DLLs. They read as Valid, organization Microsoft
  Corporation.
- **Host probe:** run on the R1 bundle (§3).
- **Not run:**
  - an R2 build, because no licensed VC\Redist files exist on this host;
  - the R2 host probe;
  - an R2 installer;
  - the clean-machine matrix.

R2 is not complete until the licence confirmation, the R2 loader probe and the
clean-machine validation pass.
