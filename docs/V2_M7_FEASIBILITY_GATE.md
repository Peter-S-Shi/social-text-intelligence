# M7 — Pre-Release Feasibility & Risk Gate: evidence and decision record

M7 asks one question: does the current Windows-first PySide6 desktop product have a
viable path to packaging and distribution, and what real blockers or hardening
priorities does that path expose? It is an evidence gate, not Product Hardening,
not packaging, and not legal certification. No installer was built, no binary was
distributed, and no product behaviour changed. The only code added is experiment
tooling under `tools/m7/`.

**Exit recommendation: CONDITIONAL.** No blocking risk was found, and the selected
route (PySide6 under LGPL-3.0, PyInstaller onedir, unbundled models) built, launched,
and completed real end-to-end inference. It is not a PASS because clean-machine
behaviour, the LGPL deliverables, and a few evidence gaps (section 9) are still
open. Those conditions are carried to M8 and M10 below, and the owner confirms the
classification at merge.

## 1. How to read this record

Every claim carries one evidence tag.

| Tag | Meaning |
| --- | --- |
| **MEASURED** | Produced by a command in this milestone, reproducible with section 10 |
| **UPSTREAM** | Read from an official upstream page or file during M7 (URL given) |
| **INFERRED** | Concluded from source code or metadata, not executed |
| **HISTORICAL** | Taken from the Architecture Gate spikes, not re-measured |
| **UNTESTED** | An assumption nobody has checked |

## 2. Environment and tested heads

| Item | Value |
| --- | --- |
| Base | `origin/main` at `86c4c3c` (PR #48, M6) |
| Tooling head tested | `14f6f2f` on branch `milestone/m7-pre-release-feasibility-risk-gate` (only `tools/m7/` added; `src/` and `tests/` identical to the base) |
| OS and hardware | Windows 11 Home 10.0.26200; Intel Core i7-12700H; 15.7 GB RAM; local SSD |
| Python | 3.12.14 in the project `.venv`, whose base interpreter is a vendored runtime, not a python.org install (see C6) |
| Key packages | PySide6-Essentials and shiboken6 6.11.2 (Qt 6.11.2), torch 2.13.0, transformers 5.14.1, tokenizers 0.22.2, safetensors 0.8.0, numpy 2.5.1, py3langid 0.4.0, PyInstaller 6.22.3, pyinstaller-hooks-contrib 2026.8 |
| Models | The two pinned revisions, imported from an existing local Hugging Face cache into a disposable per-run data root (verified by the app's own hash check); no download of weights |
| Data | Synthetic sentences only; disposable roots under an ignored `_local/` directory |
| Real user data | The real `%LOCALAPPDATA%` application folder did not exist before M7 and still does not; nothing wrote to it |

## 3. Area 1 — Qt / PySide6 LGPL and third-party obligations

### 3.1 What was actually bundled — MEASURED

The frozen build (`sti-desktop.exe` plus `sti-probe.exe` in one onedir) contains the
Qt DLLs `Qt6Core`, `Qt6Gui`, `Qt6Widgets`, `Qt6Network`, `Qt6Svg`, with Python
modules `QtCore`, `QtGui`, `QtWidgets`, `QtNetwork`, plus the platform, style,
image-format, SVG-icon, TLS and network-information plugins and the software OpenGL
fallback `opengl32sw.dll`. The application itself imports only `QtCore`, `QtGui` and
`QtWidgets` (enforced by `tests/desktop/test_boundaries.py`, and the probe confirmed
it at run time). `QtNetwork`, `QtSvg` and the plugins arrive through PyInstaller's
PySide6 hooks, not through application code. The 41 PySide6 and shiboken6 binaries
in the bundle are **byte-identical (SHA-256) to the ones in the installed wheels**,
so PyInstaller did not repack, strip or alter them.

### 3.2 Module licences — UPSTREAM

Qt's licensing page (https://doc.qt.io/qt-6/licensing.html, Qt 6.12 documentation, 2026)
lists the Qt modules that are available only under GPL-3.0 for open-source users:
Canvas Painter, CoAP, Graphs, GRPC, HTTP Server, Lottie Animation, MQTT, Network
Authorization, Qml Compiler, Quick 3D, Quick 3D Physics, Quick Timeline, Virtual
Keyboard and Wayland Compositor. **None of the five bundled Qt libraries is on that
list**, and no listed module is in the bundle. Qt Charts and Data Visualization are no
longer on the list and the page does not state their licence; they are absent from the
bundle and the imported set. The pages never write "Qt Core is LGPL" in so many words,
so LGPL eligibility of the five libraries is an inference from the exclusion list.
The installed wheel metadata declares `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`
for PySide6-Essentials and shiboken6 (MEASURED, package metadata).

### 3.3 Obligations — UPSTREAM

From https://www.qt.io/licensing/open-source-lgpl-obligations (2026, undated) and the
LGPL v3 text (https://doc.qt.io/qt-6/lgpl.html): provide the complete corresponding
source of the Qt library used, or a written offer, even when unmodified; dynamic
linking is the safe route; the user must be able to modify and relink or replace the
library and run the result (installation information); a prominent notice that Qt is
used under the LGPL, with the LGPL and GPL texts; no added terms that restrict those
rights; some distribution channels conflict. The page gives no legal advice and
recommends a commercial licence when in doubt.

### 3.4 Gaps found — MEASURED unless noted

| Finding | Detail |
| --- | --- |
| The bundle carries **no LGPL text, no Qt notice and no source offer** | The wheels ship only `LicenseRef-Qt-Commercial.txt`. No file named LGPL exists in the bundle. PyInstaller copies some third-party licence files as a side effect, which is not a compliance set |
| Qt DLLs are separate files | `_internal/PySide6/Qt6*.dll` next to the executables. This is consistent with dynamic linking and the replacement route, and is **not by itself proof** of either |
| Relink / replace was **not** exercised | No rebuilt Qt was produced or substituted. The byte-identity check above only shows the files are untouched |
| Exact-version sources exist upstream | `qt-everywhere-src-6.11.2.tar.xz` and the PySide6 6.11.2 source directory on `download.qt.io`, and tag `v6.11.2` of `pyside-setup` on `code.qt.io`, all answered HTTP 200. A source offer can point at them; whether a link satisfies the written-offer duty is a legal question left to M10 |
| The Qt for Python (PySide6) licensing page could **not** be read | The fetch returned navigation only. PySide6-specific module licensing, the Essentials/Addons split and any freezing guidance are therefore **UNTESTED** here and must be read in M10 |
| Other bundled components need notices | Qt's third-party list (https://doc.qt.io/qt-6/licenses-used-in-qt.html, UPSTREAM) names zlib, PCRE2, double-conversion, FreeType (FTL or GPL-2.0), HarfBuzz, libpng, libjpeg-turbo, DejaVu fonts, the Public Suffix List (MPL-2.0) and Mesa llvmpipe (MIT and BSL-1.0) for the matching modules. Python-side components with their own terms include torch (BSD-style plus bundled third-party notices and `libiomp5md.dll`), numpy (BSD-3-Clause plus bundled components), regex (Apache-2.0 and CNRI-Python), certifi and tqdm (MPL-2.0), and the Microsoft VC runtime DLLs. PyInstaller itself is GPL-2.0-or-later with a bootloader exception that permits embedding the bootloader in non-GPL programs (MEASURED, its `COPYING.txt`) |

### 3.5 Classification

| Risk | Class |
| --- | --- |
| No GPL-only Qt module is in the build | **CLEARED FOR NEXT PHASE** (re-check against the frozen layout at M10) |
| LGPL deliverables absent (texts, prominent notice, source offer, installation information) | **OPEN BUT MANAGEABLE** — concrete, bounded M10 work; nothing in the approved route prevents it |
| Replaceability of Qt DLLs unproven in practice | **OPEN BUT MANAGEABLE** — M10 must perform a real substitution test |
| PySide6-specific licence page unread; third-party notice set unassembled | **OPEN BUT MANAGEABLE** |
| The route is fundamentally infeasible | **Not found.** No change to the toolkit, licence route or distribution strategy is needed |

This is a preflight. It is not legal advice and not a compliance approval; the A7
gate stays open.

## 4. Area 2 — PyInstaller onedir feasibility build

All builds used `tools/m7/sti_desktop.spec` and the entry `tools/m7/entry_desktop.py`
(the real `desktop.qt.app.main`). Every figure is MEASURED.

| Build | Result |
| --- | --- |
| Build 1, default analysis | Succeeded in 43 s at about 100 MB, **but without PyTorch or transformers**: the providers load them with `importlib`, which PyInstaller cannot see. A build that "works" can therefore ship without inference |
| Build 2, explicit hidden imports and package metadata | Succeeded; 665 MB; 4,922 files; 413 s while another job shared the CPU |
| Build 3 and final build 4 (`14f6f2f`), same plus excluding dev tooling | Succeeded; **657 MiB on disk (645.7 MiB by file size), about 4,916 files, 350 s (build 3) and 336 s (build 4)** on an idle machine; four benign warnings (an optional TensorBoard import and a Linux `libgomp` path in a torch module) |
| Minimisation effect | Excluding pytest, rich, typer, click, pygments and setuptools saved about 8 MiB. The size is dominated by PyTorch (366 MB), then PySide6 (73 MB), transformers (42 MB) and numpy (21 MB) |

What it took: `torch`, `transformers`, `tokenizers`, `safetensors`, `huggingface_hub`
and the three provider modules as hidden imports; `copy_metadata` for fifteen
packages (transformers and huggingface_hub read installed versions at import); the
py3langid model file and the package JSON resources as data. I did not minimise
that list further, so some entries may be unnecessary. The spike's earlier list was
not reused blindly; this one was grown from failures and confirmed by the probes.

The real desktop executable launched from the build, showed its window titled
"Social Text Intelligence" in **0.93 to 1.67 s** (ten launches across two builds, warm
file cache), and closed cleanly through its window. Two instances launched at once
both ran (section 7). The application did not create its data folder merely by
starting.

**Not established:** a clean machine without Python or developer tools, SmartScreen
and third-party antivirus behaviour, installer creation, update flow, signing, or a
non-Windows platform. A static check (`tools/m7/dll_closure.py`) found every DLL
import in all 103 bundled binaries resolved inside the bundle or in System32, which
is a weak proxy and not proof. Defender's real-time protection was on during the
runs and recorded no detection for the build folder (MEASURED, one machine).

| Risk | Class |
| --- | --- |
| A frozen onedir with the real UI and both models is buildable and launches | **CLEARED FOR NEXT PHASE** |
| Dynamic imports hide inference dependencies from PyInstaller; a default build silently lacks them | **OPEN BUT MANAGEABLE** (the spec and a startup self-check belong in M10) |
| Clean-machine, SmartScreen, antivirus, installer | **OPEN BUT MANAGEABLE** (M10; unsigned installers were already accepted at A6) |

## 5. Area 3 — End-to-end inference with both pinned models

`tools/m7/probe_e2e.py` runs the real desktop wiring (`build_window`,
`build_desktop_services`) against a disposable root, unfrozen and frozen.

| Step | Unfrozen | Frozen (`14f6f2f` build, 3 runs) |
| --- | --- | --- |
| Models folder inspected and imported, full hash Verify | both found, imported, ready | same |
| Direct analysis, cold then warm | positive; 11.1 s cold, 0.08 s warm | positive; 6.6 to 7.6 s cold, 0.07 s warm |
| Synthetic CSV (200 valid rows plus one empty row), import, analyse, results | committed, 200 analysed; sentiment counts 75, 75, 50 | identical counts; committed in all runs |
| Language check inside the frozen app | not asserted | 200 of 200 supported (`en`), 0 unavailable (run 1 report) |
| Corruption recovery (frozen) | covered by existing tests | one byte of the emotion weights flipped: Verify reported `corrupt`; analysis then refused with the session-block error; re-import repaired it and Verify returned `ready`; analysis stayed blocked until restart, as the H2 decision requires |
| Network (frozen) | not run | the app's own transport fetched a 1,924-byte pinned `config.json` over HTTPS, about 0.2 s. This checks TLS inside the frozen app; the 1 GB download path itself was not repeated (M5.0 and M5.2 cover it) |
| Unicode and space in the data path | not run | passed with a root containing spaces and non-ASCII characters (build 3) |

The frozen run is functionally identical to the unfrozen run on the same synthetic
input. Not covered: a download-and-resume cycle in the frozen build, clicking through
the frozen UI by hand, and long inputs.

Observations for M8 to confirm, not defects asserted here:

- The quick status stayed `ready` for both models after the one-byte corruption; only
  the explicit full Verify detected it. That matches the documented "quick, read-only"
  status, but it means analysis can start on damaged weights if nobody runs Verify.
- The probe's summary showed `failed_rows = 1` for the one empty row that import had
  already rejected as invalid. Whether a rejected row should also count as an
  analysis failure is a presentation question to confirm against the M6 acceptance
  record.

| Risk | Class |
| --- | --- |
| Both models load and infer correctly in the frozen app, direct and batch | **CLEARED FOR NEXT PHASE** |
| Recovery from corruption works as the contract says | **CLEARED FOR NEXT PHASE** |
| Weights corrupted after the last Verify are not noticed before analysis | **OPEN BUT MANAGEABLE** (decision for M8) |

## 6. Area 4 — Size, start-up, first inference, memory

All MEASURED on the machine above, warm file cache. A cold-cache start (after a
reboot) was **not** measured because it needs privileges this session lacks.

| Measure | Result |
| --- | --- |
| Onedir size | 657 MiB on disk; 645.7 MiB of file bytes; about 4,916 files, of which 103 are binaries |
| Deflate-compressed copy (proxy for an installer payload) | 267 MiB with zip level 6 (Historical spike figure: 308 MB for a similar build) |
| Models | Not bundled: 1,004,464,932 bytes (0.94 GiB) fetched or imported separately |
| Build time | 336 s on an idle machine (413 s when sharing the CPU) |
| Window shown (real executable) | 0.93 to 1.67 s over ten launches; the probe's own window construction took 0.5 to 1.0 s after Qt loaded |
| Memory with the window up, models not loaded | 163 to 166 MB working set, 89 to 93 MB private (real executable); the probe measured 83 to 129 MB working set |
| PyTorch loaded before the first analysis? | No: the window and project list never import torch or transformers |
| First inference (both models, cold) | 6.6 to 7.6 s frozen; 11.1 s unfrozen |
| Warm single text | 0.07 s |
| Batch of 200 rows, both models | 9.4 to 16.7 s across runs (about 47 to 84 ms per row); the spread follows load on the machine, so treat it as a range |
| Memory after both models loaded | peak working set 1,212 to 1,260 MB; private bytes 2,049 to 2,118 MB |
| Dependency loading | `flask` never loaded; the Qt modules loaded were `QtCore`, `QtGui`, `QtWidgets` |

The probe ran inference on the main thread, so it does not measure whether the
window stays responsive during the cold load; the spike recorded a live event loop
(HISTORICAL), and the desktop runs jobs on worker threads by design (INFERRED).

| Risk | Class |
| --- | --- |
| Footprint (about 0.65 GiB installed, about 0.27 GiB compressed, plus 0.94 GiB of models) | **CLEARED FOR NEXT PHASE** as a portfolio-scale desktop product; it was the A2 trade-off |
| 1.2 GB resident and 2.1 GB private after loading; behaviour on an 8 GB or 4 GB machine unknown | **OPEN BUT MANAGEABLE** (state a minimum requirement after a low-memory test) |
| Cold-cache start-up and first-run UX | **OPEN BUT MANAGEABLE** (UNTESTED) |

## 7. Area 5 — Local data, process, SQLite and concurrent-instance risks

`tools/m7/probe_concurrency.py` drives the real services (real models) from separate
OS processes against one disposable root. Every project used 300 synthetic rows.

| Scenario | Result (MEASURED) |
| --- | --- |
| Two instances analyse the same project (offset by 3 s) | Nine of ten runs: one `committed`, the other `stale`, final state `analyzed` with 300 rows, no error, no corruption. The stale instance spends its full inference time for nothing. One run (an earlier, since-corrected probe version, run while a build was using the CPU) reported both instances `stale` and then "project no longer available" although the project file existed and later read as analysed. It was **not reproduced** in nine reruns (3 on the corrected probe plus 6 stress runs) and is **unexplained** |
| One instance deletes a project while another analyses it | Delete succeeded; the analyser ended `stale`; no file was resurrected |
| Hard kill of an instance mid-analysis | The project reopened as `ready` and unanalysed, re-analysis `committed`, final state `analyzed`; no leftover sidecar files were listed |
| Two instances import the same models folder into one directory | One finished `completed`; the other failed with the generic `storage_failed` code (the failing side varied between runs); a later re-import completed and models were ready. Nothing corrupt was left |
| Two copies of the desktop executable | Both ran side by side; no single-instance guard exists |

Reading: the revision-guarded commit in `sqlite_projects.py` does what its docstring
says. Concurrent analysis cannot silently overwrite, a killed process never blocks a
project, and a deleted project is not recreated. The weaknesses are about wasted work
and unclear messages, not data loss. **Not tested:** a full disk, a read-only or
sync-managed (for example OneDrive) data folder, antivirus locking a project file,
a very large project, a crash during the commit itself, and timing-dependent races
beyond the five scenarios.

| Risk | Class |
| --- | --- |
| Data integrity under concurrent instances, kill and delete | **CLEARED FOR NEXT PHASE** for the scenarios run |
| No single-instance guard; duplicate analysis; model-import collision shows a generic error | **OPEN BUT MANAGEABLE** (M8 priority 1) |
| One unexplained transient "not available" result | **OPEN BUT MANAGEABLE** (M8 must stress it, see backlog) |
| Disk-full, sync-folder, antivirus-lock behaviour | **OPEN BUT MANAGEABLE** (UNTESTED; M8) |

## 8. Risk register summary

| ID | Risk | Class | Owner of next step |
| --- | --- | --- | --- |
| R-L1 | No GPL-only Qt module in the build | CLEARED FOR NEXT PHASE | M10 re-check |
| R-L2 | LGPL texts, notice, source offer and installation information missing | OPEN BUT MANAGEABLE | M10 |
| R-L3 | Qt replacement never exercised | OPEN BUT MANAGEABLE | M10 |
| R-L4 | PySide6 page unread; third-party notice set unassembled | OPEN BUT MANAGEABLE | M10 |
| R-P1 | Frozen onedir builds, launches, runs both models | CLEARED FOR NEXT PHASE | — |
| R-P2 | Dynamic imports hide inference dependencies from the freezer | OPEN BUT MANAGEABLE | M10 |
| R-P3 | Clean machine, SmartScreen, antivirus, installer, signing | OPEN BUT MANAGEABLE | M10 |
| R-P4 | Build ran on a vendored interpreter in a dev environment | OPEN BUT MANAGEABLE | M10 |
| R-I1 | Frozen direct and batch inference and recovery are correct | CLEARED FOR NEXT PHASE | — |
| R-I2 | Post-Verify weight corruption not noticed before analysis | OPEN BUT MANAGEABLE | M8 decision |
| R-S1 | Size and start-up acceptable | CLEARED FOR NEXT PHASE | — |
| R-S2 | Memory floor and cold-cache start unknown | OPEN BUT MANAGEABLE | M8 |
| R-D1 | Data integrity under concurrency, kill, delete | CLEARED FOR NEXT PHASE | — |
| R-D2 | No single-instance guard; generic import-collision error | OPEN BUT MANAGEABLE | M8 |
| R-D3 | Unexplained transient "not available" | OPEN BUT MANAGEABLE | M8 |
| R-D4 | Disk-full, sync folder, antivirus lock untested | OPEN BUT MANAGEABLE | M8 |

**BLOCKING: none.** No decision at a binding gate needs reopening: toolkit (A7),
model delivery (A2), licence route, and distribution strategy are unchanged, so no
Human Gate is triggered.

## 9. Exit recommendation: CONDITIONAL

Why not PASS: the three conditions below are real, bounded and unmet, and the owner
asked that a working dev-machine build not be read as installation readiness.

1. **Clean-machine proof is absent** (R-P3). Nothing here claims installability.
2. **The LGPL deliverables do not exist** (R-L2, R-L3, R-L4). The preflight found no
   obstacle, but the A7 gate stays open and no binary may leave the owner.
3. **Evidence gaps are recorded, not closed**: the PySide6 licence page, the
   cold-cache and low-memory runs, the unexplained transient result.

Why not BLOCKED: the approved route worked end to end on the real product, no
GPL-only Qt module is involved, the data layer held under the concurrency it was
asked to survive, and every open item is ordinary engineering or compliance work.

The conditions are discharged in M8 (items 1 to 7 below) and M10 (the packaging and
compliance items). Nothing here authorises starting either milestone.

## 10. Input backlog for M8 — Product Hardening (prioritised, bounded)

M8 includes the early lightweight owner-led exploratory scenario trial. These are
inputs, not commitments; M8 sets its own scope.

| Priority | Item | Why | Bounded shape |
| --- | --- | --- | --- |
| 1 | Single-instance / cross-process exclusion (R-D2) | Two instances run today; duplicate analysis wastes minutes; model import collides | One guard for the app, or a cross-process lock for provisioning and analysis, plus a clear message instead of `storage_failed` |
| 2 | Stress the unexplained transient (R-D3) | One unexplained "not available" is the only data-visibility anomaly seen | At least 30 two-instance rounds with the file state captured on any anomaly; fix only with a failing test |
| 3 | Decide on Verify before analysis (R-I2) | Weights damaged after the last Verify are used silently | Owner decision: cheap fingerprint check at first analysis, or documented as accepted |
| 4 | Storage failure modes (R-D4) | Disk-full, read-only and synced folders are untested | Targeted probes with clear errors; no new storage design |
| 5 | Memory floor and cold start (R-S2) | 2.1 GB private after load; unknown on small machines | Measure on a constrained VM or limit; state a minimum; check the UI stays live during model load |
| 6 | Confirm the `failed_rows` count for import-rejected rows | Possible double count in the summary | Check against `V2_M6_ACCEPTANCE.md`; fix only if wrong |
| 7 | Deferred items already recorded in `PROJECT_STATUS.md` | Single-instance lock, short-text language cautions, and others | Pull in only those that item 1 to 6 touch |

Planning boundaries kept explicit: **M8** Product Hardening with an early owner-led
exploratory scenario trial; **M9** Evidence and Formal Acceptance, the full
owner-operated Scenario-Based UAT with synthetic reference data and a paginated local
HTML acceptance companion (progress, comments, exportable results); **M10**
production Windows packaging, final LGPL and distribution compliance, installer and
release-candidate verification. M7 implemented none of M9 or M10.

## 11. Input for M10 — packaging and compliance

- Build in a clean virtual environment from a standard CPython install, with only
  runtime dependencies, then pin the PyInstaller spec; add a startup self-check that
  both providers can import their libraries, so a build that lacks them fails loudly.
- Produce the LGPL set: licence texts, a prominent notice in the About surface, a
  source offer naming Qt 6.11.2 and PySide6 6.11.2 (or whatever ships), installation
  information, and a real Qt-DLL substitution test. Read the PySide6 licensing page.
- Assemble third-party notices for every shipped component (section 3.4) and re-check
  `THIRD_PARTY_NOTICES.md` against the frozen layout.
- Test on a clean Windows machine or VM, with SmartScreen and a second antivirus.
- Re-run the probes in `tools/m7/` against the production build.

## 12. Reproducing the measurements

From the repository root, in the project virtual environment with the `dev` extra,
`pyinstaller` and a local Hugging Face cache of the two pinned revisions (the M7 runs
used an ignored `model_cache/` directory):

```text
# build (about 6 minutes); M7_MINIMISE=1 excludes dev tooling
M7_MINIMISE=1 python -m PyInstaller --noconfirm --distpath _local/m7/dist --workpath _local/m7/build tools/m7/sti_desktop.spec

# end-to-end probe, frozen; use a disposable root
_local/m7/dist/sti-m7/sti-probe.exe --root _local/m7/run/root --models-src model_cache --out _local/m7/run/report.json --recovery --net

# the same probe unfrozen
python tools/m7/probe_e2e.py --root _local/m7/run_unfrozen/root --models-src model_cache --out _local/m7/run_unfrozen/report.json

# concurrency scenarios A (two analyses), B (delete), C (kill), E (model import)
PYTHONPATH=src python tools/m7/probe_concurrency.py --root _local/m7/conc/root --models-src model_cache --only A,B,C,E --out _local/m7/conc/report.json

# DLL closure proxy and byte-identity of the Qt files
python tools/m7/dll_closure.py _local/m7/dist/sti-m7
```

The concurrency probe imports the models into its root on first use. The probes use synthetic text and write only to the
paths given. Timings vary with machine load, which is why ranges are reported.

## 13. Sources

| Source | Tag |
| --- | --- |
| https://doc.qt.io/qt-6/licensing.html (Qt 6.12 docs, 2026): GPL-only module list | UPSTREAM |
| https://doc.qt.io/qt-6/qtmodules.html: module listing | UPSTREAM |
| https://www.qt.io/licensing/open-source-lgpl-obligations (2026, undated) | UPSTREAM |
| https://doc.qt.io/qt-6/lgpl.html: LGPL v3 text | UPSTREAM |
| https://doc.qt.io/qt-6/licenses-used-in-qt.html: third-party components in Qt 6.12 | UPSTREAM |
| https://doc.qt.io/qtforpython-6/licenses.html and sibling pages | Could not be read; navigation only |
| https://download.qt.io/official_releases/qt/6.11/6.11.2/single/ and the PySide6 6.11.2 source directory; https://code.qt.io/cgit/pyside/pyside-setup.git/ tag `v6.11.2` | UPSTREAM (reachability only) |
| Installed wheel metadata (PySide6-Essentials, shiboken6, PyInstaller `COPYING.txt`) | MEASURED |
| Architecture Gate spikes and decisions in `V2_DESKTOP_ARCHITECTURE_EXPLORATION.md` | HISTORICAL |
