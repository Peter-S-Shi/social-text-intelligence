# V2 Desktop Architecture Exploration

Status: **Exploration complete — awaiting the Architecture Gate (repository-owner
decision).** Evidence date: **2026-10-06**. Baseline: `main` at
`28a9b47` (V2 Product Scope Gate PASS recorded in
[V2 Product Discovery](V2_PRODUCT_DISCOVERY.md), section 11).

This is a decision record, not an implementation. No product code, test,
dependency, version, UI, or desktop migration changed on the branch that carries
this document. Disposable spikes are preserved, out of `main`, on branch
`prototype/v2-desktop-spikes` (commit `01fb597`; section 5 lists what each proved).
Live phase state is recorded only in [Project Status](../PROJECT_STATUS.md).

## 1. Method and evidence grades

- **Inputs:** the repository (code, tests, docs), four disposable spikes run on
  this Windows 11 machine with the pinned offline models, and framework/licence/
  packaging sources fetched on the evidence date.
- **Grades:** **L** = measured in this repository; **S** = measured by a spike
  (reproducible from the prototype branch); **A** = primary vendor/project page
  read on the evidence date; **B** = secondary or search-summary only, not
  load-bearing; **H** = hypothesis. Conclusions rest on L, S, and A.
- **Environment caveat.** All spike measurements come from one machine
  (Windows 11, Python 3.12, CPU-only PyTorch 2.13, Qt for Python 6.11.2,
  wxPython 4.3.1, PyInstaller 6.22.3). They show feasibility and order of
  magnitude, not release-grade numbers.

## 2. Inherited constraints

From the Product Scope Gate (discovery record, section 11) and the owner brief:

1. Persistent local projects: per-user OS application-data directory, never the
   repository; SQLite is the default direction; explicit delete, retention, and
   export; **no encryption claim**.
2. Desktop packaging and UI redesign are approved V2 goals.
3. The final product must **not** be the existing Flask/localhost app wrapped in
   a browser or WebView.
4. Moderation Training and Support Triage are demoted, preserved, and get no
   further V2 investment.
5. Language detection and an unsupported-language warning are required; French
   is not.
6. A representative-domain evaluation is a mandatory evidence gate before model
   capability claims.
7. Charter principles stand: local-first, no telemetry, licensed models only,
   logs without user text, UI contains no model-loading or database business
   logic.

## 3. V1 architecture inspection

### 3.1 What is reusable as-is (L)

- `contracts/`, `providers/`, and `services/` contain **no** reference to Flask,
  Werkzeug, or the `interface/` package (searched: zero matches). The
  dependency direction in [Architecture](ARCHITECTURE.md) holds in code.
- State objects (`BatchWorkspace`, `ReviewState`, `InsightState`) are frozen
  dataclasses; services are functions that return replacements. This maps
  naturally onto append-only rows.
- `AnalysisService.analyze`, `analyze_batch`, review rules, insight metrics, and
  CSV export shaping are pure with respect to I/O.
- Spike A (section 5) ran the real service from a native shell with no
  adaptation.

### 3.2 What lives under `interface/` and must be re-homed (L)

`interface/` is 2,523 lines of route code (`app.py` 1,282; `moderation_routes.py`
726; `triage_routes.py` 515) plus 333 lines of state. Beyond HTTP parsing and
rendering, it owns responsibilities that a desktop shell would otherwise
re-implement or duplicate:

| Responsibility | Where it lives today | Why it must move |
| --- | --- | --- |
| Composition root: building real providers from cache dir, offline flag, threshold | `app.py` `_real_analysis_service`, defaults in `create_app` | Desktop needs the same wiring without Flask config |
| Limits and defaults (rows, bytes, TTL, capacities) | `app.config.from_mapping` in `create_app` | Settings must be shared, typed, and not a Flask mapping |
| Workspace store, expiry, capacity, tokens | `batch_state.py`, `moderation_state.py`, `triage_state.py` (three near-identical classes) | Replaced by the persistent project repository; the in-memory form is still needed for tests and the legacy surface |
| Atomic read-modify-write and analysis lease | `workspace_mutation.py`, `EphemeralBatchStore.begin_analysis/complete_analysis` | The concurrency rule ("compose on latest state; one analysis at a time; rejected write-back is a conflict") is domain behaviour, not HTTP behaviour |
| Use-case orchestration: lease, analyze, create review state, empty insight state, commit | closure `batch_analyze` in `app.py` | The "analyze this batch into this workspace" use case has no home outside a route |
| Review save: accept-both vs update, then navigation to next/next-unreviewed | closure `save_review` in `app.py` | Same |
| Insight selection resolution (saved selection vs request, defaults, validation) | `requested_insight_selection` in `app.py` | Business rules written against `request.values` |
| Context-note add/remove commit logic | closures `mutate_note` in `app.py` | Same |
| User-facing error mapping | `_safe_error` in `app.py` | Message policy must be shared by every shell |
| Security boundary (Host/Origin/CSP/size) | `app.py` before/after_request | Genuinely HTTP-only; **not** needed by a desktop shell and retires with the web surface |

### 3.3 One hard gap for a desktop UI (L)

`analyze_batch(preview, analyzer)` is synchronous and monolithic. It exposes no
progress callback and no cancellation. A 500-row batch took about 40 s in V1
capacity evidence ([REAL_MODEL_CAPACITY_EVIDENCE](REAL_MODEL_CAPACITY_EVIDENCE.md)),
so a desktop shell needs progress and cancel. This is a small, additive change
to `services/` (an iterator or callback) and is listed as seam S6.

### 3.4 Do existing boundaries materially block the desktop target? **No.**

The service layers are framework-free and were driven directly by Qt and wx
shells. What is missing is an application layer, not a repaired boundary. The
conditional `/improve-codebase-architecture` pass was therefore **not**
triggered; the extraction needed is bounded and is specified in section 8.

## 4. Desktop approaches considered

All candidates were judged against: in-process use of the existing Python and
PyTorch stack, licence fit for an MIT public repository, Windows fit, packaging
maturity, accessibility, maintenance cost, and the owner constraint against a
web-app wrapper.

| Option | Licence (A) | Maturity (A) | Accessibility | Verdict |
| --- | --- | --- | --- | --- |
| **PySide6 (Qt Widgets)** | LGPL-3.0, GPL-2.0, GPL-3.0 or commercial; PyPI wheels valid for open source | 6.11.2, 2026-08-18, "Production/Stable", Python 3.10–3.14 | Qt exposes platform accessibility APIs; Windows backend is UI Automation (B); known per-widget gaps reported (B); accessible interface present in spike | **Recommended** |
| wxPython | wxWindows Library Licence (OSI) | 4.3.1, 2026-07-30, "Mature", Python 3.10–3.14 | Native Win32 controls; reports of screen-reader label regressions (B) | **Fallback** (spiked, works) |
| PyQt6 | GPL-3.0 or paid commercial | 6.11.0, 2026-03-30 | Same Qt | Rejected: GPL would constrain the MIT repo, or needs a paid licence |
| Tkinter/ttk | PSF (stdlib) | Bundled | No accessibility statement on the official page; known weak (H) | Rejected on evidence gap; not spiked |
| Flet (Flutter) | Apache-2.0 | 1.0.0 only released 2026-09-14; 1.0.3 on 2026-09-30 | Vendor claim only | Watch; PyTorch compatibility with its embedded runtime unverified |
| Toga/BeeWare | not retrieved (bot wall) | not retrieved | not stated | Not assessed |
| Tauri or Electron plus Python sidecar | Tauri sidecar documented for PyInstaller-built binaries (A) | Mature shells | Web accessibility is strong, and V1's A8 hardening could carry over | Rejected for V2.0: second language/toolchain, IPC boundary, still ships the full Python/PyTorch bundle as a sidecar, and the UI is a WebView |
| .NET (WPF/WinUI) plus Python sidecar | n/a | n/a | Strong platform | Rejected: second ecosystem, IPC; no evidence it pays for itself (H) |
| Flask or pywebview wrapper around the V1 app | n/a | n/a | n/a | **Excluded by owner constraint** |

**Why PySide6.** It keeps one language and one process, so the proven path is
a direct function call with no serialisation. It offers an LGPL licence route
suitable in principle for an open-source MIT repository (compliance steps still
to be confirmed, risk R3), a production-stable release line with current Windows
support, and an accessibility layer that, per secondary sources, is built on
Windows UI Automation rather than a custom canvas (B; to be audited, risk R4).
The footprint difference is modest: Qt costs about 48 MB more than wx in the
spike, against a roughly 930 MB application dominated by PyTorch. wxPython
remains the credible fallback if Qt licensing or accessibility proves
unacceptable.

**What V1 accessibility work does not carry over.** The A8 semantics and
keyboard recovery live in HTML templates. A native shell must be audited anew
(accessible names, tab order, focus return, screen-reader table navigation).
This is an explicit cost, not an assumed carry-over.

## 5. Spike results (S)

All code is on `prototype/v2-desktop-spikes`; each answers one question.

### Spike A — native Qt shell calls the V1 service directly

Result: **PASS.** A PySide6 window drove `LazyAnalysisService` with the real
pinned models, offline, on a worker `QThread`, with no HTTP.

| Observation | Result |
| --- | --- |
| Flask or http.server imported | No / No |
| Three analyses through the shell | all returned; model revision `3216a57f` recorded |
| Cold first analysis (torch import plus both model loads) | about 24.0 s |
| Warm analyses | 0.08–0.09 s |
| UI event loop during the cold analysis | about 1,186 timer ticks at 20 ms: the UI stayed live |
| Accessible interface for the button | present; accessible name set |

**Finding that matters.** The first version deadlocked: a bare lambda connected
to a cross-thread signal ran in the worker thread and touched widgets. The fix
is the standard rule that results must reach the UI through a QObject slot. A
real implementation needs a small job-runner abstraction so this cannot recur.

**Cold-start finding.** 24 s is far above the 3.6 s warm-cache initialisation in
the A4 capacity evidence. That figure was measured with a hot disk cache; a
desktop first launch will feel this, so the shell must show a loading state and
may preload models in the background at startup.

### Spike A-wx — same question for wxPython

Result: **PASS** (mock providers). In-process call from a worker thread via
`wx.CallAfter`, accessible name set. Frozen size 44.8 MB versus 92.9 MB for the
Qt shell. Real-model behaviour is identical because it is the same service call.

### Spike B — persistence boundary

Result: **PASS with one important correction.** Stdlib `sqlite3` (SQLite 3.53.1)
was enough; no new dependency.

| Question | Result |
| --- | --- |
| Per-user directory without a new dependency | Resolved `%LOCALAPPDATA%\SocialTextIntelligence` through the Windows Known Folder API via `ctypes` |
| AI and human records kept separate | Schema keeps `analysis` and `human_review` as separate tables; reviews are revisioned with a unique `(record, revision)` |
| Is delete real | With `secure_delete=ON`, deleted text was **not** found in the main file or WAL after delete or after `VACUUM`. With `secure_delete=OFF` (the SQLite default) deleted text **was still recoverable** from the database files after `DELETE` and after a bare `VACUUM` |
| Cascade | Deleting a project removed its records, analyses, and reviews (`ON DELETE CASCADE`) |
| Reader and writer connections | WAL: a reader saw only committed state during an open write transaction and the new state after commit |
| Interrupted write | A child process killed mid-transaction left only the committed project; `integrity_check` was `ok` |
| Retention | A purge query removed an expired project and its children |
| Export | A joined export of text, AI report, and human judgment worked |

The correction: SQLite's defaults would make "delete project" look successful
while leaving text on disk. The design must set `secure_delete=ON`, checkpoint
the WAL, and word the UI as "removed from the application's files", not as
forensic erasure (SSD wear levelling, OS backups, and file-history are outside
the application's control).

### Spike C — packaging path (PyInstaller onedir)

**C1, Qt shell with mock providers (no PyTorch):** build 41 s; **92.9 MB**;
frozen executable ran the full flow in 0.8 s and recorded `torch_imported: false`
and an accessible interface. Largest single files are the software OpenGL
fallback (19.7 MB) and the Qt core libraries; a trimmed Qt payload could reduce
this (not attempted).

**C1-wx, wx shell with mock providers:** **44.8 MB**, ran correctly.

**C2, Qt shell with PyTorch, transformers, and the real offline models:**
**PASS.** The frozen onedir executable ran the three-text flow with the real
pinned models loaded from an external cache directory, and recorded the same
model revision as the unfrozen run.

| Measure | Result |
| --- | --- |
| Build time (analysis plus collection) | 204 s |
| Onedir size, **excluding model weights** | **928 MB**, 4,925 files |
| Largest components | `torch` 361 MB, `PySide6` 72 MB, `transformers` 36 MB, `numpy.libs` 20 MB |
| Same folder, deflate-compressed (a proxy for installer payload) | 308 MB |
| Cold first analysis in the frozen app | about 30.9 s (unfrozen: about 24.0 s); warm 0.09 s |
| UI event loop during the cold analysis | live (about 1,500 timer ticks at 20 ms) |
| Models | read from an external directory by path; nothing bundled |

What this exposes:

- **The footprint is dominated by PyTorch, not by the GUI toolkit.** Switching
  from Qt to wx saves about 48 MB of a roughly 930 MB application. Toolkit choice
  should therefore be made on licence, accessibility, and maintenance, not size.
- **Installer reality.** Application about 0.3 GB compressed plus about 0.95 GB of
  weights (which compress poorly) is about 1.3 GB if bundled; about 0.3 GB if
  weights are fetched on first run. This is the main input to decision A2.
- **Resource handling works for externally supplied models.** Passing the model
  directory by path is enough, which supports a first-run download into a
  per-user models directory. First-run download itself was **not** prototyped.
- **Packaging needs deliberate hooks.** The PyInstaller build used explicit
  hidden imports and metadata copies for fifteen packages (PyTorch,
  transformers, tokenizers, safetensors, huggingface_hub, numpy, and others) and
  emitted benign warnings (for example an optional TensorBoard import). I did
  not test which of those options are strictly necessary, so a production build
  needs its own minimisation pass and a clean-machine run.
- **Not tested:** antivirus and SmartScreen behaviour, a clean machine without
  Python installed, installer creation, update flow, and code signing.
- **Invalid first attempt, discarded.** The first C2 build produced an
  executable that exited silently. The cause was my own workflow error: the
  entry script was removed from disk by a branch switch while the build was
  still running. The rebuild from an isolated checkout of the prototype branch
  is the result reported above. It is not a product or toolchain blocker.

## 6. Packaging, licensing, and footprint conclusions

**Recommended path (subject to the owner decisions in section 11):** PySide6 in
PyInstaller **onedir** (not onefile), delivered by a **per-user, non-admin
installer** (Inno Setup is a candidate), **unpackaged** rather than MSIX.

- **Why onedir.** The LGPL route relies on the user being able to replace the Qt
  libraries; PyInstaller's documentation states onefile extracts to a temporary
  folder at every launch and onefile Qt deployment is reported unreliable (B).
  Onedir also starts faster and is easier to debug (A, PyInstaller docs).
- **Why not MSIX for V2.0.** MSIX runs apps in a container that virtualises or
  redirects some file-system writes (A, Microsoft overview). The Product Scope
  decision requires data in the real per-user application-data directory and
  explicit delete/export semantics; container redirection would complicate
  every claim about where data lives. Revisit only if store distribution
  becomes a goal.
- **Signing and antivirus.** PyInstaller bundles are commonly flagged by
  antivirus heuristics, and unsigned executables raise SmartScreen warnings (B).
  A code-signing certificate is a real recurring cost and still does not
  guarantee zero detections. For a portfolio audience this is a presentation
  risk to accept knowingly or to budget for.
- **Qt licensing obligations.** PySide6 is offered under LGPL-3.0 or GPL for
  open-source use (A, PyPI). Compliance details (notice, source offer, library
  replaceability) were **not** confirmed from a readable primary page in this
  exploration; the official Qt LGPL obligations page must be read before the
  first public installer (H, unresolved risk R3). Qt Charts and Data
  Visualization are GPL-only per the Riverbank FAQ for PyQt (A); do not use them
  in V2 without re-checking for PySide6 Addons.
- **Models.** The two pinned models are about 0.95 GB of unique weight files; the
  local V1 cache is 1.4 GB because it also holds a redundant `pytorch_model.bin`
  for the sentiment model (L). Bundling them would put an installer near or above
  2 GB. Recommended approach: do **not** bundle weights; download the pinned
  revisions on first run from the original licensed repositories into a
  per-user models directory, with progress, checksum/revision verification, and
  a resumable offline mode. This matches the Charter's stance against
  redistributing weights, and the Charter itself does not forbid a one-time
  first-run download. It does introduce a first-run network step that the V1
  quick start already has; owner approval is requested (A2).
- **Where the size goes.** In the frozen application PyTorch is about 361 MB of
  928 MB (S). A CPU-only build is essential; the project environment already
  uses the CPU wheel, and a CUDA wheel was not measured. The PyTorch Windows
  wheel size was not stated on the pages read (A), so it is not quoted.

## 7. Persistence boundary design

**Location.** `%LOCALAPPDATA%\SocialTextIntelligence\` on Windows (Known Folder
API, spike B). Not Roaming: project text must not sync (A: LocalAppData is
per-user, non-roaming). Other platforms are out of scope until a platform
decision is made; the same module resolves a conventional path elsewhere but is
**untested** (H).

**Layout (recommended).** `projects\<project-id>.sqlite3`, **one database file per
project**, plus a small `settings.json`. Per-project files make delete an
explicit file removal after the in-database purge, make export a copy plus a
documented export format, isolate corruption, and avoid a cross-project query
need that does not exist. A single shared database is the alternative; it is
simpler for listing but worse for delete and isolation. This is decision A3.

**Schema direction (from spike B).** Tables: `project`, `record`, `analysis`
(immutable, with model revisions and the full report), `human_review`
(revisioned), plus context notes and later derived views. This mirrors V1's
immutable-AI-beside-separate-human rule. Revisioning is a **V2 design addition**:
V1's `HumanReview` holds only the current judgment and overwrites it on update,
so keeping history is a deliberate extension for auditability that the owner
may accept or drop when the schema is detailed.

**Operational rules.**
- `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, **`secure_delete=ON`**, and a
  checkpoint after destructive operations (spike B).
- Schema version in `PRAGMA user_version`; forward-only, additive migrations
  (Charter 11.4) with an automatic file copy before any migration.
- Writes in short `BEGIN IMMEDIATE` transactions; analysis results committed
  per batch with the V1 conflict semantics preserved; a single-writer rule per
  project file and a lock file to detect a second app instance.
- No user text in logs; exception messages must not echo record text.

**Delete, retention, and export semantics.**
- *Delete:* user-initiated, per project, with a confirmation that states exactly
  what is removed ("removed from this application's data files; copies you
  exported or that your operating system or backups hold are not affected").
- *Retention:* each project carries an optional retention period; default is
  keep until deleted (the purpose of persistence); expiry is evaluated at
  application start and shown, never silent. Default policy is decision A4.
- *Export:* explicit, per project, to a user-chosen location, in the existing
  formula-safe CSV forms plus a complete project export; nothing leaves the
  application data directory without a user action.
- *Encryption:* **not claimed.** The database is plain SQLite. User-facing text
  and docs must say project data is stored unencrypted in the user's
  profile and rely on operating-system account protection. Any future
  encryption is a separate decision needing its own threat model.

## 8. Recommended target architecture

```text
desktop UI (PySide6)         legacy Flask UI (compat/dev only)       CLI
        \                              |                              /
         +--------------- application layer (new, framework-free) ----+
                           use cases, settings, error messages,
                           job runner contract, ports (ProjectRepository,
                           ModelProvisioner)
                                       |
              services/  (analysis, batch, review, insights, export;
                          decision-practice modules untouched)
                                       |
              providers/  --  contracts/
                                       |
        infrastructure: SQLite repository, model downloader, paths
```

Principles: dependencies point inward; the application layer imports no Qt and
no Flask; the desktop shell never touches `sqlite3` or model libraries
directly; the persistent project is the new "workspace".

### Migration seams (ordered)

| Seam | Change | Needed before desktop migration |
| --- | --- | --- |
| S1 | Extract `AppSettings` and a composition root (`build_analysis_service`) from `create_app` and `_real_analysis_service` | Yes |
| S2 | Define the application-layer use cases currently in route closures: analyze batch into workspace, save review (+navigation), resolve insight selection, add/remove notes, exports | **Yes**, and highest value |
| S3 | Move user-facing error mapping (`_safe_error`) into the application layer | Yes |
| S4 | Introduce a `ProjectRepository` port with an in-memory implementation that reproduces today's lease/atomic-mutation behaviour, so S2 can be tested without SQLite | Yes |
| S5 | Implement the SQLite repository and model provisioner behind the ports | Part of the first implementation milestone |
| S6 | Add progress and cancellation to batch analysis (iterator or callback) | Yes |
| S7 | Re-point Flask routes at the application layer so the legacy surface cannot diverge | Yes, otherwise two copies of the rules drift |
| S8 | Language detection and unsupported-language signalling in the application layer (Q3) | Before the first release |

**Left where they are:** moderation and triage routes, state, and services (Q2).
They keep their own ephemeral stores; no application-layer extraction for them
in V2.

### The legacy Flask UI

Recommendation: **keep it as a frozen compatibility/development surface through
V2 development, then retire it at a later explicit gate.** Reasons: it holds the
only UI for Moderation Training and Support Triage, which Q2 preserves; its 5.7k
lines of tests are the regression net while services are re-homed; it lets
seams S2 and S7 be checked behaviourally. Constraints: no new features, clearly
marked legacy in its docs, a single shared set of use cases (S7), and an
explicit retirement decision (A5). Retiring it earlier would orphan the
preserved decision-practice material.

## 9. How the Q5 evidence gate fits the architecture

- Every stored `analysis` row carries model identity and revision (spike B
  schema), so any later evaluation is reproducible against exact models.
- Human reviews are revisioned and kept separate, so reviewed rows can be
  exported as a labelled dataset without re-keying; this is the natural input
  for a representative-domain evaluation.
- No architectural component should make a capability claim (for example a
  "reliable" badge or accuracy figure). User-facing claims must reference an
  evaluation record once such a record exists.
- The evaluation procedure itself (sample design, labelling protocol, metrics)
  is not decided here; it belongs to a later milestone.

## 10. Risks and unknowns

| ID | Risk or unknown | Severity | Mitigation or next step |
| --- | --- | --- | --- |
| R1 | Packaged size and startup: 928 MB application before weights, 30.9 s frozen cold start (spike C2) | High | Decide model strategy (A2); minimise the build; measure on a clean machine |
| R2 | Antivirus and SmartScreen friction for unsigned PyInstaller output | Medium | Accept for portfolio or budget signing (A6) |
| R3 | Qt LGPL compliance steps not confirmed from a primary page | Medium | Read the official Qt LGPL obligations page before any public installer |
| R4 | Qt accessibility on Windows has reported widget gaps (B); V1 A8 gains do not transfer | Medium | Plan an accessibility audit as a milestone gate; keep wx as fallback |
| R5 | Cold start about 24 s on first analysis | Medium | Background preload plus loading state |
| R6 | Cross-thread UI mistakes (spike A deadlock) | Medium | One job-runner abstraction; code review rule |
| R7 | First-run model download is a network step and a failure mode | Medium | Resumable, verified, offline-first; clear errors |
| R8 | Persistence at rest widens the privacy surface | Medium | Honest wording, delete semantics, no encryption claim, no logs of text |
| R9 | Two UIs drift during migration | Medium | S7; frozen legacy surface |
| R10 | Platform scope is only verified on Windows 11 | Low | Declare Windows-first (A1) |
| U1 | Other Python-GUI options (Toga, Flet with PyTorch) were not fully assessed | Low | Revisit only if PySide6 fails a gate |
| U2 | Real-model quality on representative text (Q5) is unmeasured | n/a here | Later evaluation milestone |
| U3 | Qt Quick or QML would give a more modern UI at the cost of a second language; not assessed | Low | Out of scope for the architecture decision |

## 11. Architecture Gate brief

**Recommendation.**

1. Build V2 as a native **PySide6 (Qt Widgets) desktop application** running the
   existing services in-process; keep wxPython as the documented fallback.
2. Introduce a framework-free **application layer** by executing seams S1–S4,
   S6, and S7 **before** any desktop UI work.
3. Persist projects as **one SQLite file per project** under
   `%LOCALAPPDATA%\SocialTextIntelligence\projects`, with `secure_delete=ON`,
   explicit delete, retention, and export, and **no encryption claim**.
4. Package as **PyInstaller onedir plus a per-user installer**, unpackaged;
   **do not bundle model weights**; download pinned revisions on first run.
5. Keep the Flask UI as a **frozen legacy compatibility surface**; retire it at
   a later gate.
6. Keep Moderation Training and Support Triage untouched in the legacy surface
   for V2.0.

**Decisions that require the repository owner.**

- **A1. Platform scope.** Windows-first (verified here) with other platforms
  explicitly unclaimed? Recommendation: yes.
- **A2. Model delivery.** First-run download of the pinned revisions (no
  bundled weights), versus an installer that bundles roughly 1 GB of weights?
  Recommendation: first-run download, with an offline model-pack option later.
- **A3. Persistence layout.** One SQLite file per project, versus a single
  shared database? Recommendation: per-project files.
- **A4. Default retention.** Keep until deleted, versus a default expiry?
  Recommendation: keep until deleted, with a visible per-project retention
  setting.
- **A5. Legacy Flask surface.** Keep frozen through V2 development and decide
  retirement later, versus retire at the desktop milestone? Recommendation:
  keep frozen; decide later.
- **A6. Signing.** Accept unsigned installers for portfolio use, versus budgeting
  for a code-signing certificate before public distribution? Recommendation:
  accept unsigned until a public release is planned, and say so in the docs.
- **A7. Toolkit.** Approve PySide6 under its LGPL route, with wxPython as the
  fallback, subject to reading the official Qt LGPL obligations before the
  first installer? Recommendation: approve.
- **A8. Moderation and Triage in the desktop product.** Leave them only in the
  legacy surface for V2.0 (recommended), or require a desktop home for them?

Nothing else is escalated. Implementation does not start before the Gate
decision.

## 12. Reproducing the spikes

From a scratch virtual environment that exposes the V1 source and dependencies
read-only (a `.pth` file pointing at the V1 `src` and `site-packages`) with
`PySide6-Essentials`, `wxPython`, and `pyinstaller` installed, using the files on
`prototype/v2-desktop-spikes` under `prototypes/v2-desktop-spikes/`:

```text
python spike_a_native_shell.py [--mock] [--cache-dir model_cache]   # spike A, headless
python spike_a_wx_shell.py                                          # spike A-wx
python spike_b_sqlite_store.py                                      # spike B, scratch dir wiped
pyinstaller --noconfirm --onedir --exclude-module flask \
  --exclude-module torch --exclude-module transformers spike_a_native_shell.py   # C1
pyinstaller --noconfirm --onedir --exclude-module flask --hidden-import torch \
  --hidden-import transformers --collect-data transformers \
  --copy-metadata torch --copy-metadata transformers  <and the other metadata
  packages listed in section 5> spike_a_native_shell.py                         # C2
```

Run the packaged build from a checkout of the prototype branch, not from a
working tree that may change branch mid-build (see the discarded first C2
attempt). Spikes use only synthetic text and write no project data.

## 13. Source provenance

All sources accessed 2026-10-06.

| Claim | Source | Grade |
| --- | --- | --- |
| PySide6 6.11.2 (2026-08-18), Python 3.10–3.14, LGPL/GPL/commercial, "Production/Stable" | https://pypi.org/project/PySide6/ | A |
| Qt exposes platform accessibility APIs; keyboard and system palette support | https://doc.qt.io/qt-6/accessible.html | A |
| Qt Windows accessibility backend is UI Automation; widget-specific gaps reported | Qt source log, Qt bug tracker and forum search results | B |
| PyQt6 GPL-3.0 or commercial; commercial needed unless app is GPL-compatible; some Qt modules GPL-only | https://pypi.org/project/PyQt6/ , https://www.riverbankcomputing.com/commercial/license-faq | A |
| wxPython 4.3.1 (2026-07-30), "Mature", wxWindows Library Licence, Windows wheels about 18.5 MB | https://pypi.org/project/wxPython/ | A |
| wxPython uses native Windows controls; screen-reader label regression reports | https://discuss.wxpython.org/ threads from search results | B |
| Flet 1.0.0 on 2026-09-14, 1.0.3 on 2026-09-30, Apache-2.0, Flutter-based | https://pypi.org/project/flet/ | A |
| Flet `flet build windows` embeds Python in-process; will not compile missing binary wheels | Flet docs search results | B |
| Toga page unreadable (bot wall) | https://pypi.org/project/toga/ | not retrieved |
| Tkinter: dated appearance, ttk themed widgets, no accessibility statement read | https://docs.python.org/3/library/tkinter.html | A (partial) |
| PyInstaller 6.22.3 (2026-09-12); onedir vs onefile behaviour | https://pypi.org/project/pyinstaller/ , https://pyinstaller.org/en/stable/operating-mode.html | A |
| Nuitka 4.2.2, AGPL with runtime exception, needs a C compiler | https://pypi.org/project/Nuitka/ | A (partly summary) |
| PyInstaller antivirus/SmartScreen friction; signing helps but does not eliminate | search results | B |
| onefile Qt deployment and LGPL replaceability | PySide deployment docs via search results | B |
| Tauri sidecar bundles PyInstaller-built binaries; per-triple naming; capability config | https://v2.tauri.app/develop/sidecar/ | A |
| Electron embeds Chromium and Node.js | https://www.electronjs.org/docs/latest/ | A (licence not stated) |
| Inno Setup: per-user and admin installs, one-file installers, licence terms | https://jrsoftware.org/isinfo.php | A |
| MSIX containerisation virtualises or redirects some writes; packages must be signed | https://learn.microsoft.com/en-us/windows/msix/overview | A |
| FOLDERID_LocalAppData is per-user, non-roaming | https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid | A |
| SQLite public domain; 3.53.x current | https://www.sqlite.org/ | A |
| PyTorch 2.14.1 on PyPI (2026-09-30); Windows CPU index lists +cpu wheels | https://pypi.org/project/torch/ , https://download.pytorch.org/whl/cpu/torch/ | A (sizes not stated) |
| Local footprint, interface-layer analysis, spikes A, A-wx, B, C | this repository and `prototype/v2-desktop-spikes` | L / S |
