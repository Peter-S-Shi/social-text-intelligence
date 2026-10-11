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

The six DLLs are placed in **`_internal\`**, beside `python313.dll`. They are not
placed beside the executables. The independent Spec review caught that the first
draft of this milestone got this wrong.

| Load path | Search behaviour | Where the runtime is found |
| --- | --- | --- |
| Bootloader loads `_internal\python313.dll`, which imports `vcruntime140.dll` | `LOAD_WITH_ALTERED_SEARCH_PATH`: the DLL's own folder **replaces** the executable's folder; then System32, the Windows folder, the current directory and `PATH` | `_internal\` (the DLL's own folder) |
| CPython loads `.pyd` extensions (PySide6, shiboken6, NumPy, tokenizers, ...) | `LOAD_LIBRARY_SEARCH_DEFAULT_DIRS` plus the extension's folder | An already-loaded module with the same name is reused; a first load relies on `_internal\` being a DLL directory, as set by the PyInstaller bootloader |
| Qt plugins, PyTorch `torch\lib`, `ctypes` by-name loads | Default directories plus `os.add_dll_directory` folders | Same as above |

**Placement beside the executables would fail.** It would not be searched for
`python313.dll`'s imports. A clean machine would then reach it only through the
current directory, which is the application folder only when STI is started from
the Start Menu shortcut.

**Only measurement decides the second and third rows.** They rest on the
bootloader's DLL directory, so the loader reasoning is a hypothesis.
`tools/m10/runtime_origins.ps1` measures it:

- It launches `sti-desktop.exe` with a **neutral working directory**, so a copy
  that is reachable only through the current directory cannot pass.
- It waits for the main window.
- It requires all six DLLs to be loaded, each from `_internal\` (R2) or from
  System32 (R1).
- It closes only the process it started.

A wrong location is caught even on a host that has the system runtime: the
system copy would be loaded instead of the app-local one.

**Measured on the R1 bundle on the development host:**

- At window time all six DLLs were loaded. Startup alone covers the whole
  closure, PyTorch included.
- Every one came from System32: `origins_ok` was true for R1.
- The same bundle checked as R2 correctly failed.

The R2 probe on an R2 bundle has not been run, because no licensed files exist yet.

`sti-check.exe` uses the same bootloader and the same `_internal\`. Its loading
is exercised by its three frozen checks on the clean machine. `--smoke` imports
Qt and opens a window. Its modules are not separately listed, because the process
exits within seconds.

## 4. Licensing facts (read 2026-10-11)

The owner chose **Visual Studio Community 2026**. Microsoft's "older downloads"
page (2026-07-13) says older versions need an active subscription and does not
list Community 2022. With owner approval, the two licence documents linked from
the Visual Studio licence directory were downloaded and read. They are kept
locally and not committed:

| Document | Last updated | SHA-256 |
| --- | --- | --- |
| Microsoft Software License Terms, Visual Studio Community 2026 (`VS2026_Comm_ENU.1033`) | 2025-10-01 | `02ac0763…e1fb` |
| Microsoft Visual C++ V14 Redistributable and Runtime (`Cpp_v14_ENU.1033`) | 2025-10-01 | `08651651…c783` |

**Community 2026: who may use it** (§2 of the licence, paraphrased):

- **Individual:** an individual working on their own applications may use it to
  develop and test them, "either to sell or for any other purpose".
- **Organization:** any number of users may use it for OSI-licensed open-source
  applications, classroom training, academic research and certain other uses.
  Otherwise, up to five concurrent users may use it if the organization is not an
  enterprise.
- **Enterprise:** an organization whose group has more than 250 PCs or users, or
  more than US$1 million in annual revenue. An enterprise may use it only for the
  listed uses.
- **Preview builds:** Insiders/preview components are for internal evaluation only
  and must not be distributed.

**Distributable Code** (§7 of the licence):

- The object code on the Distributable List (`aka.ms/vs/18/redistribution`) may be
  distributed with applications the licensee develops.
- That list (learn.microsoft.com, Visual Studio 2026 Redistribution, 2025-11-11)
  allows any file under `VC\redist`, **unmodified**. The `debug_nonredist` folders
  are excluded. The Visual Studio 2026 runtime folder is `Microsoft.VC145.CRT`,
  which the tooling finds as `Microsoft.VC1xx.CRT`.
- **The distributor must:**
  1. add significant primary functionality (STI does);
  2. require distributors and external end users to agree to terms that protect the
     Distributable Code at least as much as the licence;
  3. indemnify, defend and hold Microsoft harmless from claims related to the
     distribution or use of the application, except claims based solely on the
     Distributable Code.
- **The distributor must not:**
  - distribute preview components;
  - use Microsoft trademarks in the application's name or to suggest Microsoft
    endorsement;
  - make the Distributable Code's source subject to an "Excluded License" (a
    copyleft licence).

**The V14 Redistributable and Runtime terms** are the end-user terms of the
runtime itself:

- use is allowed on any number of devices;
- no reverse engineering, removal of notices or separate distribution;
- the trade-law terms apply;
- the software is provided "as is" with limited damages.

**Other Microsoft pages** (learn.microsoft.com):

- App-local deployment into the executable's folder is supported but not
  recommended, for servicing reasons.
- Microsoft cannot update local copies; the application owner must redeploy them.
- On Windows 10/11 the system UCRT is always used.

**Engineering response to requirement 2:**

- An R2 installer now shows `tools/m10/R2_END_USER_TERMS.txt` as an
  acceptance-required licence page (Inno `LicenseFile`). R1 installers show none.
- That text is a **draft** derived from the protections above and is marked
  "NOT APPROVED".
- Whether it is sufficient is an owner/legal decision. So is how it sits next to
  the LGPL's §4 requirement to allow reverse engineering for debugging
  modifications of the Qt combination: the draft limits reverse engineering only
  for the Microsoft files.

Indemnifying Microsoft (requirement 3) is an obligation the owner takes on; it
cannot be engineered.
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
   - verifies the import closure (§2) and copies the six files unmodified into
     `_internal\`;
   - accepts no runtime file anywhere else.

   The packet (`legal/inventory.json`, `microsoft_runtime`) records the route, the
   shipped files and the pin match. It derives B3 as open until the owner's licence
   confirmation is recorded in the manifest. `build-evidence.json` records the
   route, the measured imports and the staged receipts.
3. **Probe on the host:** run `tools/m10/runtime_origins.ps1 -Route R2` on the
   frozen bundle. All six modules must load from `_internal\`, even where a
   system runtime exists.
4. **Installer.** `installer.py` re-hashes any runtime file against the committed
   pin. It admits them only as the complete pinned set in `_internal\`. It then renders `RequireSystemRuntime = False` and the
   end-user terms page (§4), and records the terms' SHA-256 in its receipt. The
   per-user, never-elevating setup (`PrivilegesRequired=lowest`) stays unchanged.
5. **Clean-machine validation:** `validate_installer.ps1 -EnvironmentKind DisposableVM`.
   For an R2 receipt it first asserts:
   - none of the six DLLs is in System32 or a `PATH` folder;
   - neither the native nor the WOW6432Node `VC\Runtimes\x64` key exists;
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

Decided in this milestone: product **Visual Studio Community 2026**; licence
documents downloaded and read (§4).

Still needed:

1. **Eligibility and obligations (owner/legal confirmation).**
   - Confirm that the owner's use falls under the individual licence, or under a
     non-enterprise organization of up to five users.
   - Accept the indemnity obligation.
   - Approve, or replace, the draft end-user terms (§4), including how they sit
     next to the LGPL.
   - These are recorded together as `owner_licence_confirmation` in
     `distribution/vc-runtime.json`. The record must name the edition, the channel
     (Stable, not Insiders), `confirmed_on`, `confirmed_by`, the pinned
     `redist_version` and the approved terms' SHA-256. B3 stays open for an R2
     packet unless every field is present and the version and hash match the
     current pin and terms. Re-pinning new bytes clears the record. The tooling
     never infers it.
2. **Installation (owner action).**
   - Install Visual Studio Community 2026 from the Stable channel with the
     "Desktop development with C++" workload, and accept its licence.
   - The same installation can also provide the E4 Qt rebuild toolchain (B6). E4
     pins the Visual Studio 2022 compiler (MSVC v143, `cl` 19.44) that matches the
     official Qt build. Visual Studio 2026 offers it as the optional individual
     component "MSVC v143 – VS 2022 C++ x64/x86 build tools"; also add a Windows 11
     SDK. Whether that exact component is offered still has to be checked in the
     installer.
   - Installing it is not, by itself, B3 clearance.
3. **Isolated Windows environment (owner action).** This development host runs
   Windows 11 Home, which has neither Windows Sandbox nor Hyper-V. Provide a
   VirtualBox/VMware VM, or a second PC, that has all of the following:
   - a fresh Windows 10/11 x64 install;
   - a standard (non-administrator) user;
   - a confirmed absence of the VC++ runtime;
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

- **Full local suite:** 1,249 passed, 6 opt-in skipped; Ruff and strict MyPy pass.
- **Unit tests** (`tests/tools`): 114 passed, 2 skipped (frozen-bundle tests need
  an explicit bundle). New tests cover:
  - signer, lookalike-signer, version and byte refusal;
  - pin recording that leaves the confirmation unset;
  - the import-closure guard;
  - app-local placement only in `_internal\`, and the installer re-hashing against the pin;
  - the confirmation fields and the reset on re-pin;
  - R2 B3 derivation;
  - installer prerequisite and terms-page rendering for R1 and R2.
- **Real signatures:** the signature and version reader was exercised on real
  Microsoft-signed system DLLs. They read as Valid, organization Microsoft
  Corporation.
- **Host probe:** run on the R1 bundle (§3). It now uses a neutral working
  directory and retries the close request; three consecutive runs passed.
- **Independent review fixes** (Spec and Standards, after the first two commits):
  - the placement moved from beside the executables to `_internal\` (§3);
  - the probe requires the full six-DLL set and does not rely on the working
    directory;
  - an empty or stale licence confirmation no longer clears B3;
  - re-pinning new bytes clears the confirmation;
  - the installer re-verifies the runtime files against the committed pin instead
    of trusting the packet's flag;
  - the clean-machine baseline checks all six DLLs, `PATH` and both registry
    views;
  - a PowerShell timeout no longer surfaces as a traceback.
- **R1 regression rebuild:** the new packaging inputs were built on the default
  route at `0f7afd5`. Results:
  - 5,256 files, the same as M10-E2;
  - `microsoft_runtime_route` R1 with no runtime file;
  - the build-time closure is identical to §2;
  - the packet is valid, with B1/B4/B5 derived;
  - the frozen `--license-info`, `--verify-runtime` and `--smoke` checks exit 0;
  - the DLL-origin probe passes, with all six from Windows.
- **Not run:**
  - an R2 build, because no licensed VC\Redist files exist on this host;
  - the R2 host probe;
  - an R2 installer;
  - the clean-machine matrix.

R2 is not complete until the licence confirmation, the R2 loader probe and the
clean-machine validation pass.
