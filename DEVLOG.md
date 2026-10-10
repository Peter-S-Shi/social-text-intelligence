# Development Log

## M10-A — Production Packaging Foundation and owner sequencing

The owner explicitly reprioritized M10 engineering from merged main `26e1d08`.
M9.0 remains a historical approved design, M9.1 COMPLETE and merged; M9.2–M9.4
are deferred without acceptance or waiver of Q5 evidence for model claims.
Production-oriented PyInstaller onedir configuration follows M7, with pinned
build dependencies, explicit dynamic model imports, language resources, offline
startup verification and a bounded temporary-data smoke. Model weights stay
unbundled. M7/M8 risks remain unchanged. Optional owner 30-minute smoke is
planned NOT RUN; no installer, distribution, LGPL-compliance or release claim.

Actual Windows artifact `302d9f5` passed both frozen native-Qt regressions and
the bounded DLL closure proxy. Implementation HEAD `49f8771` passed fresh
Python 3.11/3.12/3.13 CI (1,165 passed / 8 skipped each) and Node (12 passed).
Independent review findings were repaired and re-reviewed; post-merge governance
wording is consistent. The final evidence closeout is documentation-only
`[skip ci]`, preserving separate artifact, application-test and CI provenance.


## M9.1 — UAT Infrastructure

Delivered a versioned project-authored `SYNTH_UAT` CSV/long-text recipe and
24 reserved scenario families with 49 stable atomic steps. A separate offline
HTML companion records authorized observations with strict versioned JSON,
derived progress, local draft recovery, safe import/export and linked retests.
Core, fixture and real-browser checks validate the recorder only: all actual
Windows UAT/accessibility steps remain NOT RUN. M9.2 source authorization,
independent second-annotator availability and execution preregistration remain
future gates. M7/M8 open risk dispositions are unchanged; M9.3/M9.4 and M10
remain unstarted. No STI product behavior, model evaluation or release claim
changes here.

Validation is recorded against implementation HEAD `bdd3b080` in the
[M9.1 validation record](manual-qa/m9-uat/VALIDATION.md): local Python
1154 passed / 4 opt-in skipped, Node 11 passed, and fresh three-version
GitHub CI plus the recorder job PASS. The final documentation-only closeout
uses `[skip ci]`; actual formal UAT remains NOT RUN.

## M9.0 — Owner Evidence Design Gate PASS (2026-10-10)

After PR #53 independent review and its targeted README correction, the owner
explicitly approved the substantive M9.0 design on reviewed HEAD `32d8d37`:
180 real-primary, 45 separate synthetic challenge, and at least 60 independent
double-blind reference targets; three channels, task-specific denominators,
2,000 fixed-seed stratified bootstrap resamples and 95% percentile intervals.
This approves the design, not any named source's rights, the availability of a
second annotator, any executed evaluation/UAT or overall M9 acceptance. The
original design-delivery entry below documents its historical pre-approval state.
At the M9.0 Gate decision, M9.1 had not started. M7/M8 risk dispositions
remain unchanged.
This governance-only decision record uses `[skip ci]`.

## M9.0 — Evidence Design Gate: design delivery (historical pre-approval record)

Encoded the owner-approved English software/app domain and Strategy A into four
coherent evidence, evaluation, Windows UAT and exit-gate design records, using
`45874bb` as the planning baseline. The proposed 180 primary records, 45 separate
challenge cases and at least 60 dual-blind labels await owner M9.0 Gate approval;
no named source is authorized. The design separates owner design freeze from the
later source-bound execution preregistration and reports uncertainty/inference
coverage independently for sentiment, dominant emotion and non-neutral sets.
M7's CONDITIONAL exit and M8's unresolved/owner-decision/unverified observations
remain intact. No data acquisition, fixtures, labels, model runs or product changes
were made. At that historical design-delivery point, M9.1–M9.4 had not started.
Engineering review and document merge do
not constitute owner Gate approval or overall M9 completion. Validation was
limited to local lifecycle/link checks and targeted assertion lint; the design
closeout uses `[skip ci]`. See the [contract](docs/V2_M9_EVIDENCE_CONTRACT.md).

## V2 Product Hardening & UI Fidelity — M8 owner acceptance PASS

On 2026-10-10, the repository owner explicitly confirmed completion and approval
of M8 manual acceptance, including the UI fidelity outcome and the early owner-led
exploratory product trial. The overall M8 decision is **PASS**. No per-step results
or filled friction log were provided, so none are inferred from this decision.
Track A's measured but unresolved risks and owner decisions retain their individual
dispositions. The exploratory trial does not replace M9's formal acceptance.
At the M8 acceptance exit, M9 — Evidence & Formal Acceptance was next for
Codex and had not started. V2 remained not release-ready; live state is recorded
in Project Status.

## V2 Product Hardening & UI Fidelity — M8 Track B Native UI fidelity alignment — implementation complete

Track B compared the nine Round 3 reference screens with the real Windows Qt app,
captured Before and After from the real platform plugin with an unmapped
`QWidget.grab()` (exact reference geometry, nothing else on the desktop to capture),
and closed the visible gaps in two rounds. Round 1: a light sidebar and near-black
actions, a Review queue beside peer AI and human cards, two-pane Analyze one text,
metadata chips on Import, big sentiment counts on Results, numbered Insights controls
with side-by-side group cards and a hero statement on the first-run window. A strict
reflow test checks every page at 900 px against the headless platform's wider fonts,
which exposed width locks the Windows captures had hidden. Round 2, after Track A
merged: per-project row counts and review progress in the project list (six small
read-time `COUNT(*)` queries, no text, no schema change), review-state tabs, a full
row preview on Import and a read-only TEXT column on Results, both built from a
sanitized excerpt of at most 100 characters (a shorter record appears in full), and the nine
compact scores drawn as columns. Independent reviews found a wrong queue counter
under a filter, invisible focus rings on filled controls and unescaped text in
tooltips, all repaired test-first. System fonts stay; the OFL facts for the reference
fonts are recorded for the owner. At the Track B implementation exit, subjective
design fidelity and the exploratory trial were pending; the owner's later overall
PASS is recorded above. See the
[Track B record](docs/V2_M8_TRACK_B_FIDELITY.md).

## V2 Product Hardening — M8 Track A Technical Product Hardening — complete at Track A exit

Track A turned the open M7 observations into bounded fixes and measurements, with no
new feature. Two application instances are now excluded where it matters, by OS-level
file locks that vanish with their process: one project's analysis, commit and delete,
and every models-folder operation; the loser gets an actionable message instead of a
generic storage error or minutes of wasted inference. The unreplicated "project not
available" event did not reproduce in 128 stress rounds, but two adjacent listing
hazards were found and fixed. Disk-full, read-only and in-use faults now report
accurately with no partial commit. The project summary no longer counts import-rejected
rows as analysis failures. The cost of re-hashing the weights and a native-crash band
under a low memory limit are measured and left to the owner. See the
[Track A ledger](docs/V2_M8_TRACK_A_LEDGER.md). At the Track A exit, Track B and
the owner's review were pending; the later M8 owner PASS is recorded above.

## V2 Pre-Release Feasibility — M7 Pre-Release Feasibility & Risk Gate — conditional

M7 built the current desktop with PyInstaller (onedir) and ran it, without producing
an installer. The frozen build completed direct and batch analysis with both pinned
models, matching the unfrozen run, and recovered from a damaged weight file as the
contract requires. A first default build silently omitted PyTorch because the
providers import it dynamically, so the spec names those imports. Concurrency probes
with separate processes showed the revision-guarded commit keeps data intact;
the weaknesses are wasted duplicate analysis, a generic model-import error, and one
unexplained transient result that M8 should stress. The LGPL preflight found no
GPL-only Qt module, and found that the bundle carries no LGPL text, notice or source
offer. The exit is CONDITIONAL; see the
[M7 record](docs/V2_M7_FEASIBILITY_GATE.md). No product code changed.

## V2 Native UI Integration — M6 Full UI Integration / Polish — complete

M6 presents the existing V1 score breakdowns, per-row import and analysis
reasons, filtered Results with normalized export, and Agreement detail in the
native project-centred desktop. The [F-ID acceptance record](docs/V2_M6_ACCEPTANCE.md)
maps every retained feature to tests and scenes; Moderation Training and Support
Triage remain outside the V2 desktop under U4.

The final layout pass found that Review forced horizontal scrolling in a 900px
window. Its fixed two-column cards, action row, export row, and long native-score
control set a combined minimum width larger than the viewport. Review now stacks
the AI and human cards at narrow widths, wraps actions and export controls, and
keeps the wide layout when space returns. A Qt regression checks both widths.

Record navigation briefly disables the focused control while loading; Qt moved
focus to the sidebar, leaving the next record without keyboard focus. Review now
remembers focus across that busy interval, moves to the first human judgment on
a new record, and focuses the erroneous field after validation failure. A Qt
regression drives both paths. The capture script's no-match scene was also
corrected to show an actual empty result.

The actual Windows Qt scene set was regenerated at normal and 150% scaling:
[88 synthetic screenshots](manual-qa/m6-visual-evidence/README.md) cover narrow
windows, progress and cancellation, partial Review, Agreement, Insights,
export, focus, and unsaved-change states. Local full regression passed (966
tests, 4 opt-in model/network tests skipped); Ruff, strict MyPy, compileall,
and pip check passed. Independent Spec and Standards reviews passed after a
visual-evidence timing correction. This does not close formal accessibility,
model evaluation, hardening, LGPL, packaging, or release gates.

## V2 Functional Development — M5.6 Language Detection and Unsupported-Language Warning — complete; M5 Functional Exit PASS

M5.6 delivered V2-3: a local check of each analysed text's language, and a warning
wherever model labels would otherwise be read without it. It translates nothing,
reclassifies nothing, blocks nothing, and claims no multilingual capability.

Decisions worth keeping:

- The detector was chosen from a bounded spike. `lingua` needs Python 3.12 and is
  about 290 MB; `langdetect` is non-deterministic unless seeded and unmaintained;
  `py3langid` is BSD-3-Clause, small, deterministic, loads its bundled model
  without pickle, and supports 3.10 to 3.14. A 74-text synthetic set showed a
  clean gap between real text (scores 0.63 and up) and text with too little
  language (0.16 and below), so the threshold is 0.5. That shows the policy is
  sensible; it is not an accuracy claim.
- Supplied language and detected language are different facts and coexist. The
  models no longer see a supplied tag at all, because a CSV field must not decide
  model support. That is a behaviour change: a row tagged `fr` used to fail with
  `unsupported_language` while the same text untagged was analysed.
- False English defaults were the real hazard: import stored `en` for an empty
  cell and direct analysis hard-coded it. Both now record nothing, and the
  Insights Language grouping reads the supplied value from the file, which also
  regroups older projects truthfully without rewriting them.
- Migration needed no schema change: a stored report with no language entry
  decodes as *not assessed*, which shows no warning and runs nothing.
- A missing or failing detector is a visible result, never *supported*, and a
  malformed detector answer is a failed check, not a crash. The first draft
  treated a service with no detector as a silent pass; review caught it.
- Review found Moderation and Triage snapshots and the Flask Insights page
  showing model evidence with no language evidence, web warnings that relied on
  colour alone, and, on the final head, a packed export cell that made a failed
  check look like an old result.
- CI went red on Python 3.12 and 3.13 only. The new dependency brings NumPy; its
  2.5 stubs use `type X = ...`, which MyPy rejects at the repository's deliberate
  3.11 check level, and MyPy reached them through pytest's typing-only import.
  Running MyPy with a newer `--python-version` locally had hidden it; the lesson
  is to run the exact CI command. The fix keeps 3.11 and stops MyPy at the NumPy
  boundary, with a test that fails if repository code ever imports NumPy.

M5 Functional Exit audit: PASS. V2-1 to V2-4 exist behind stable application
contracts and are reachable in the native desktop. The audit also recorded, rather
than hid, V1 detail views the desktop does not yet present (score breakdowns,
per-row validation and failure reasons, a results view with filters, and the
agreement confusion and confidence bands); they are M6 integration inputs. The
classification of those as presentation, not missing capability, is a judgement the
owner can overturn at the M6 boundary.

At the M5 exit, the next planned work was M6 Full UI Integration / Polish. The
M6 section above records its later completion; V2 remains short of release
readiness.

## V2 Functional Development — M5.5 Native Insights, Context Notes, and Representative Cases — complete

M5.5 closed the largest remaining native gap: the desktop could analyse, review,
and export a project but had no surface for the grouped insights, the notes, or
the representative cases. It exposes the existing insight system and adds no
analytics of its own: a thin `InsightsWorkflow` composes the existing use cases,
and every denominator, membership, eligibility, agreement, threshold,
case-selection, note-validation, and export rule stays in the insight service.

Decisions worth keeping:

- A requested view is validated before it is saved. The shared `resolve_insights`
  saves the selection as a side effect and falls back to a default view on a
  validation error, so a typo in a date could have replaced the saved view.
  `apply` now runs the service's own validation first and raises instead.
- The two approved views are two pages of one Insights surface (a tab bar over two
  plain pages, because a tab widget sized itself to the taller page and stretched
  the controls). Agreement lives in the perspective choice.
- Sample-size handling follows the service: the warning text, the de-emphasised
  percentages, and a comparison caution come from `SampleSizeAssessment`. The
  service does not forbid a comparison of small groups, so neither does the UI;
  it says so.
- Notes are written through the repository's atomic current-state mutation, so a
  note or a saved view never replaces another process's newer notes or human
  reviews. A deterministic hook at the commit point proves it.
- A note saved before a failed refresh is cleared from the draft with a truthful
  message, because keeping it would let a retry save it twice.
- The unsaved-note guard follows the M5.4 lesson: confirming a discard must really
  discard, and a case cannot open in Review while the surface is busy.
- The export save moved to a shared `exporting.py` so the reviewed and insights
  exports share one explicit atomic write and one fixed failure message.

Process notes: reviewing the first screenshot showed the controls panel stretched
by a tab widget and unchecked list indicators that could not be seen, both fixed
before the review. A first draft of the context line, `N eligible of M group
rows`, mixed a metric-specific number with an unfiltered one and was reworded.
Typing a space in the editable note value was erased because the draft stripped it;
a test now types one.

**Next:** M5.6, Language Detection and Unsupported-Language Warning (V2-3), chosen
from the remaining approved scope: it is the only approved V2 feature with no
implementation. Packaging, the formal accessibility audit, and the LGPL gate
follow and need their own scoping.

## V2 Functional Development — M5.4 Native Human Review and Reviewed Export — complete

M5.4 closed the next product gap: an analysed project could not be reviewed or
exported from the desktop. It adds a Review page that shows the immutable AI
record and the human judgment as two separate blocks, saves judgments through the
existing review use cases and repository, shows progress and agreement, and
exports the reviewed CSV only to a path the person chooses. The review rules,
filters, navigation, agreement, and spreadsheet-safe export were reused, not
rewritten: a thin `ReviewWorkflow` in the application layer is the only new seam.

Decisions worth keeping:

- Stale writes are caught where the data is written. `save_review` now takes the
  review the person was looking at and compares it with the stored review inside
  the repository's atomic mutation, raising `ReviewConflict` on a difference. The
  newer judgment is kept and shown. The same check protects the frozen Flask
  surface for its read-to-write window. Qt knows nothing about it.
- A conflict replaces the person's draft with the newer saved review rather than
  merging, because a draft shown beside someone else's saved state is ambiguous;
  the message says the unsaved change was not saved.
- The AI block is built from labels only, and a test asserts it holds no input
  widget, so a prediction cannot be edited by accident.
- Navigation treats the just-saved record as part of the queue. Review found that
  under the Unreviewed filter, Save and next jumped back to the first match,
  because the saved record had left the filter.
- Export writes a temporary file beside the target and replaces it, so a failed
  write never leaves a half-written file, and the message carries no path.
- Unsaved changes are confirmed before anything that would drop them: navigation,
  filters, leaving the page, switching sidebar pages, and closing the window.
  Confirming the sidebar prompt must also discard: an external review found that
  the first version only switched the page, so the draft came back on return. The
  controller now has an explicit `discard_changes()` that restores the saved review
  and keeps the position.

Process notes: Qt's `clicked(bool)` was first taken as the `advance` argument by
a bound method, so saved notices silently disappeared; the buttons now use
lambdas, and a test covers the notice. The first CI run failed only because
`mypy` also checks `tests`, which a local `mypy src` run had not covered.
A word-wrapped label in the Review page looked clipped in the first screenshot,
which turned out to be a stale layout in the capture, not a defect.

**Next:** M5.5, Native Insights, Context Notes, and Representative Cases, chosen
from the remaining gap: the desktop has no native surface for the grouped AI,
human, and agreement insights, the notes, the representative cases, or their
export. Language detection and packaging come later.

## V2 Functional Development — M5.3 Native Project Workflow — complete

M5.3 closed the desktop workflow gap with one truthful path: import one CSV,
choose the text column when the file has none, create a durable project, analyse
it with visible row progress and Cancel, reopen it later, and delete it. Nothing
from the existing CSV rules, leases, or atomic commit was reimplemented: a small
`ProjectWorkflow` in the application layer orchestrates `ApplicationUseCases` and
the persistent repository, and the desktop only renders it.

Decisions worth keeping:

- Whole-run failures fail the whole run. The batch used to record every provider
  error as a row failure. For the desktop, anything that makes analysis
  unavailable (models not ready, the H2 session block, a model-load or missing
  runtime failure) is an `AnalysisUnavailableError`: the batch re-raises it, the
  lease is released, and nothing is committed. Review caught that a model-load
  failure still committed an all-failed result that could not be retried.
- An analysed project is never re-analysed, and a batch with no valid rows runs
  nothing, so a future review state can never be reset by accident. External
  review found that the first version only checked in the workflow: another
  process could analyse the project between that check and the lease, and this
  process would then replace its result. The guard now lives in
  `ApplicationUseCases.analyze_workspace`, on the leased workspace, so it holds
  for every caller and across processes; a deterministic two-workflow regression
  covers it.
- The repository now raises a dedicated `ProjectBusy` (still a `RuntimeError`) so
  the workflow does not map every `RuntimeError` to "busy".
- Error recovery resyncs: when a project is gone or changed, the list and the open
  project are reloaded, chained so a pending window close cannot start a listing
  after shutdown.
- Text analysis and project analysis do not run together.
- Delete is confirmed and worded as removal from this application's data files; it
  claims no secure erasure and says nothing about exported copies or backups.

Process notes: the first draft of the Qt tests used a gateway that answered every
record with the same report, which the store rightly refused; the test fixture now
uses a gateway that answers each record. Two repository-wide `ruff` runs reformatted
unrelated files and were reverted immediately; only new files are formatted.

**Next:** M5.4, Native Human Review and Reviewed Export, chosen from the remaining
gap: a user can now analyse a project but cannot record a judgment or take the
result out. Insights, notes, language detection, and packaging come later.

## V2 Functional Development — M5.2 Native Desktop Shell + Model Provisioning UI — complete

M5.2 built the smallest real PySide6 / Qt Widgets shell that carries the approved
M5.1 provisioning experience and wired it to the M5.0 `ModelProvisioning` port,
without duplicating backend rules. The setup window, the sidebar Models status,
the Models window, download with Stop and resume, discard, folder inspect then
verified import, Verify, error recovery by code, details, and analysis gating all
work against a fake provisioner and against the real provisioner with a synthetic
manifest.

Design choices worth keeping:

- Everything except `desktop/qt/` is Qt-free: a controller, pure view models, and
  wording. A test enforces the dependency direction, that the desktop layer never
  imports SQLite, model libraries, an HTTP client, or Flask, and that only three Qt
  modules are imported.
- One job runner: workers run off the UI thread and results come back through a
  single queued signal to a `QObject` slot, which is the rule that avoids the
  deadlock seen in the architecture spike. Progress is coalesced to the latest
  value. Verify has no Stop; closing refuses while it runs.
- H2 is one `AnalysisGate` wrapping the analysis gateway, so every entry point
  passes it. Review also closed a window where a Verify finishing while the first
  analysis was still loading would not have latched the block.
- Context pages are only what provisioning and gating need: a Projects list and
  Analyze one text. No synthetic production data and no project creation.

Review found one real bug (a folder check started from a failure result never
showed its findings), a stale Try again target after a folder check, and test
hang risks, plus dead code and a wrong claim about what the Qt wheel contains.
All were fixed. A process note: a pytest run hung once because a failing test left
a held worker thread alive, so held workers are now released in a `finally`.
CI needs the Qt runtime libraries on Ubuntu and runs the Qt tests with
`STI_REQUIRE_QT=1` so they can never skip silently.

Qt is on the LGPL-3.0 route and recorded in the notices; the pre-distribution
LGPL gate has not passed. Fonts use system fallbacks.

**Next:** M5.3, Native Project Workflow (CSV import into a persistent project,
batch analysis with progress and cancellation, open and delete), scoped from the
actual remaining gap: the desktop has no way to create a project yet.

## V2 Functional Development — M5.1 Model Provisioning UI/UX Design — complete

M5.1 designed the desktop model-provisioning experience from the M5.0 contract,
with H2 as the one explicitly approved semantic amendment (recorded below), and
passed its Human Gate on 2026-10-07. It
produced no production code. The evidence is the sidecar branch
`prototype/m5-1-model-provisioning-uiux` at `d0abd7a`, pushed to `origin` and
deliberately never merged: a design brief that maps each screen, state, action,
and error to the contract, an interactive prototype whose state machine mirrors
the M5.0 rules, and 29 deterministic state captures.

The owner approved two binding decisions:

- **H1:** the design is the M5.2 implementation baseline. M5.2 may polish
  visuals but must not reinvent the interaction model.
- **H2:** if explicit Verify confirms corruption after the analysis service has
  already loaded, all further analysis is blocked for the rest of that process.
  Repairing the files does not re-enable it; a restart re-checks readiness and
  loads the verified models fresh. No in-process unload or reload is introduced.

H2 is stricter than the M5.0 text, which let a loaded service keep working until
the next start. The governance closeout amended
[docs/MODEL_PROVISIONING.md](docs/MODEL_PROVISIONING.md) §9 to match. The backend
is unchanged: its readiness gate already blocks at the next start through the
durable Verify marker, and the in-session block is UI session state.

**Next:** M5.2, the next development sub-milestone and the start of the
continuous Loop Engineering phase. It establishes the minimal native PySide6
desktop shell (approved at the Architecture Gate, with the LGPL compliance gate
tracked from dependency introduction) and implements the approved experience
over the M5.0 contracts.

## V2 Functional Development — M5.0 Model Provisioner Function Contract & Foundation — complete

M5 opens V2 Functional Development. M5.0 has two outputs. The first is the
durable product/function contract,
[docs/MODEL_PROVISIONING.md](docs/MODEL_PROVISIONING.md), detailed enough for
M5.1 to design the provisioning experience without inventing semantics. It
covers:

- both pinned models and their files;
- five readiness states and what each allows;
- first use and explicit download;
- progress, cancellation, and the bounded pause/resume form (keep the partial;
  resume with `Range`);
- offline/pre-provisioned folders (inspect read-only, import with verification);
- wrong-revision and incomplete material, fixed error codes with recovery,
  analysis gating, and the complete list of UI actions.

The second output is the smallest UI-neutral boundary that satisfies the
contract:

- typed state and the `ModelProvisioning` port in the application layer;
- `LocalModelProvisioner` and a stdlib HTTPS transport in infrastructure;
- an offline-only composition root for analysis.

**Approved decisions kept:**

- weights are not bundled;
- analysis never downloads;
- model ids, revisions, and licences are unchanged;
- nothing substitutes or silently repairs a model.

The real pinned files were hashed into the manifest from the existing local
cache and confirmed against the original repositories over HTTPS.

**Found during implementation:** Batch analysis records each row's provider
error as a failed row, so a not-ready model would have committed an all-failed
result. `ModelsNotReadyError` now propagates and the lease is cancelled.

**Independent two-axis review.** The review found no standards violation or
scope creep. Fixed with regression tests:

- a body ending early was discarded as a checksum error instead of kept for
  resume;
- progress went backwards during verification;
- hashing could not be cancelled;
- an empty discard selection discarded everything;
- import cleanup could mask the reported outcome;
- a refused redirect response was left open;
- contract wording overstated a few behaviours.

**Validation:**

- 333 passed and 4 optional tests skipped.
- All four integration tests pass when enabled. These include a real import
  and verification of both models and offline analysis from the managed
  folder.
- Ruff, MyPy and `compileall` are clean.
- 15 safety mutations are each caught.

**Final review: a contract blocker found and fixed.**

- **The blocker:** a Verify `corrupt` finding for a same-size tampered file was
  not retained. The next quick status reported `ready` again, and the
  readiness gate could pass.
- **The fix:** Verify now records an empty per-file marker that the hash-free
  status reads, so the finding survives later status checks and restarts, and
  analysis is blocked. A verified download or import clears the marker, as
  does a matching Verify. Verify is now exclusive with Download and Import.
- **The re-review** found that a read error (for example a Windows sharing
  violation) would have been persisted as `corrupt`. Verify now reports
  `storage_failed` instead and records nothing for that file.

**Final implementation head `3f27297`:**

- remote CI PASS on Python 3.11, 3.12 and 3.13;
- local suite: 342 passed and 4 optional tests skipped;
- all 22 safety mutations are caught.

**Next (at the time):** M5.1, Model Provisioning UI/UX Design, performed
separately by the UI-design sidecar/session.

## V2 Persistent Project Foundation (M4) — complete

M4 adds the durable local-project layer behind the M3 `ProjectRepository`
boundary, with no UI, model provisioner, language detection, or packaging.
`SqliteProjectRepository` keeps one SQLite file per project under an injectable
app-data root (production default: Windows per-user LocalAppData; other platforms
are unclaimed). `PersistentProjectRepository` adds only `create_project` and
`list_projects`; `get` is open and `delete` is removal from the application's
data files. A project can be closed, the process restarted, and the imported
input, immutable AI records with exact provider provenance, human judgments,
insight state, context notes, and failures reopen without loss: values are
rebuilt through the original constructors, and floats and timestamps round-trip
exactly.

Design choices worth keeping: leases stay process-local so a crashed analysis
never wedges a project, and a per-project revision makes a stale lease fail
rather than overwrite another process's change; analysis commits in one
transaction so cancellation commits nothing partial; `secure_delete=ON` plus a
content purge, WAL checkpoint, and sidecar and migration-backup removal precede
unlinking, and the wording stays "removed from the application's data files",
never forensic erasure; schema identity uses `application_id` and `user_version`
with forward-only migrations that re-check the version under the write lock and
back up first; listing never migrates or writes.

The independent review's real findings were fixed before merge: `raise ... from
None` still left the original exception (which can hold user text) on
`__context__`, so errors are now raised outside the handler; migration ordering;
listing side effects; WAL checkpointing after writes; and `rename_project` plus
stage and row-count listing fields were removed as beyond the approved boundary.
One process slip is worth recording: a repository-wide `ruff format` reformatted
46 pre-existing files and was reverted immediately; only new files are formatted.
A final independent review then blocked the merge on a deletion defect: `delete()`
keyed off the main database file, so after a partial deletion that removed the
main file but not a migration backup, a retry reported nothing to delete and
left data behind. Managed files (database, sidecars, migration backups) are now
discovered by project id, only for the exact names the store creates, and
listing shows residue-only ids so they can be deleted. Re-review also caught
that purging followed a symlink to a file outside the projects directory; it now
skips symlinks. A further review closed the same trust boundary on open:
a managed-name symlink (database, SQLite sidecar, or backup) is never opened as a project (it is listed as unreadable
and delete removes only the link), and a symlinked migration-backup path makes a
migration fail instead of writing outside the projects directory. Implementation
commit `77d57be` passed CI on Python 3.11/3.12/3.13 first; after the
symlink-boundary fixes, final implementation commit `b91694d` also passed CI on
Python 3.11/3.12/3.13. The later governance-only head is a `[skip ci]` commit and
has no CI run of its own.
Deferred: a single-instance lock file, project rename and derived listing
summaries, and wiring any UI to the repository. Docs updated:
[Architecture](docs/ARCHITECTURE.md), `PROJECT_STATUS.md`, `ROADMAP.md`, and the
README banner; the lifecycle test's phase assertions follow.

## V2 UI/IA Gate — PASS

The repository owner closed the UI/IA Gate. Round 3 of the throwaway UI/IA
exploration is the approved V2 baseline: visual treatment may be polished, but
the project-centred information architecture, the strict V1-plus-gate-approved
feature boundary, and the visual/semantic separation of immutable AI records
from human judgment are fixed. V2-4 means batch progress plus cancellation with
M3's atomic no-partial-commit behavior; the prototype's "finished rows survive
cancellation and can resume later" behavior is not approved and may only be
reconsidered in a future persistence/job milestone. Model provisioning requires
progress, recovery, and offline/pre-provisioned support, with pause/resume only
an implementation candidate. Moderation Training and Support Triage are retired
from the V2 product surface (V1 `0.10.0` and repository history preserve them;
no code was removed). The durable record is
[docs/V2_UI_IA_DECISION.md](docs/V2_UI_IA_DECISION.md); the prototype branch
`prototype/v2-ui-ia-exploration` was not merged or copied.

`PROJECT_STATUS.md`, `ROADMAP.md`, and the README banner advance so that, after
merge, the next mainline milestone is M4 — V2 Persistent Project Foundation.
The lifecycle-consistency test's phase assertions were updated to match
(documentation-consistency checks only). No product code, dependency, version,
or prototype branch changed.

## V2 Architecture Gate — PASS

The repository owner approved A1–A7 with binding refinements and replaced A8:
Windows-first; pinned model weights downloaded explicitly on first use (with
progress, recovery, and an offline/pre-provisioned path) rather than bundled;
one SQLite file per project under per-user LocalAppData, kept until manually
deleted with no automatic expiry; Flask frozen as a development/compatibility
surface and never a runtime dependency of the final desktop product; unsigned
portfolio installers with honest SmartScreen documentation; PySide6 (Qt
Widgets) with a wxPython fallback and a mandatory pre-distribution LGPL
compliance gate. A8 no longer commits Moderation Training and Support Triage to
"legacy-only for V2.0": they get no foundation investment and their final
disposition (a single demoted native surface or explicit retirement) belongs to
the later UI/IA gate.

The architecture record's licensing section was rewritten from the now-readable
official Qt LGPL obligations page: onedir is helpful but not proof of
compliance; notice, source, relink/replacement, and installation-information
obligations apply; GPL-only Qt modules must be avoided. SQLite deletion
language stays conservative, and WAL/sidecar cleanup is deferred to the
persistence implementation. `PROJECT_STATUS.md`, `ROADMAP.md`, and the README
banner advance to V2 Application Foundation with seams S1–S4, S6, and S7 as
the implementation boundary; the lifecycle test was updated. No product code,
dependency, version, or prototype branch changed.

## V2 Desktop Architecture Exploration — complete, awaiting Architecture Gate

Inspected the V1 architecture (services/providers/contracts contain no Flask
references; route-level orchestration, three near-identical ephemeral stores,
settings defaults, and error mapping live under `interface/`), evaluated desktop
approaches against current framework/licence/packaging sources, and ran
disposable spikes: a PySide6 shell and a wxPython shell calling the V1 service
in-process (the Qt shell with the real pinned offline models), an SQLite
persistence boundary (including a delete-semantics finding: SQLite's default
leaves deleted text recoverable unless `secure_delete` is on), and PyInstaller
onedir packaging with and without PyTorch. Spike code is preserved, out of
`main`, on `prototype/v2-desktop-spikes`. The durable record is
[docs/V2_DESKTOP_ARCHITECTURE_EXPLORATION.md](docs/V2_DESKTOP_ARCHITECTURE_EXPLORATION.md),
ending with the Architecture Gate brief and owner decisions A1–A8.

Governance change is minimal: `PROJECT_STATUS.md` and `ROADMAP.md` record the
Architecture Gate as pending the owner's decision, and the lifecycle test row was
updated. No product code, dependency, version, UI, or desktop implementation
changed; V1 and earlier V2 records are untouched.

## V2 Product Scope Gate — PASS

The repository owner decided the Product Scope Gate: Q1 persistent local
projects in a per-user application-data directory (SQLite default direction,
explicit delete/retention/export, no encryption claim); Q2 Moderation Training
and Support Triage kept, folded, and demoted; Q3 French not required, with
language detection and an unsupported-language warning required; Q4 audience
is the repository owner and portfolio reviewers; Q5 representative-domain
evaluation is a mandatory evidence gate before capability claims. Recorded in
section 11 of `docs/V2_PRODUCT_DISCOVERY.md` without rewriting the discovery
evidence above it.

`PROJECT_STATUS.md`, `ROADMAP.md`, and the README banner now name V2 Desktop
Architecture Exploration (preparing the Architecture Gate) as the current
phase, stated as the post-merge truth; the Architecture Gate is recorded as
not started. The lifecycle regression test was updated to match. No product
code, dependency, version, prototype, or desktop work changed.

## V2 Product Discovery — cycle opened, discovery complete

Reopened the project for a V2 cycle from the verified public V1 `0.10.0`
baseline (`main` `5572b4b696edce646feb29795dad2a10f3be4a62`). Inspected the
repository, lifecycle documents, architecture, tests (195 passed, 2 opt-in
real-model tests skipped), and the real V1 product, including a five-sentence
offline probe of the pinned models. Researched overlapping products at the
capability level against primary vendor/project pages and recorded grade-A/B
provenance, including three self-check corrections (dropped an unverified
ATLAS.ti claim, a third-party Azure moderator retirement claim, and an
off-topic LLM-sarcasm study). The durable record is
[docs/V2_PRODUCT_DISCOVERY.md](docs/V2_PRODUCT_DISCOVERY.md); it ends with the
Product Gate brief (thesis, prioritised directions, rejected/deferred items,
unknowns, and owner decisions Q1–Q5).

Governance change is minimal: `PROJECT_STATUS.md`, `ROADMAP.md`, and the
README banner now name V2 Product Discovery as the current phase while
keeping the V1 final phase as a labelled historical row/section; the
lifecycle regression test was updated to match, following the earlier
stale-phrase pattern. No product code, behavior, dependency, or version
changed, and no prototype or implementation was started. Earlier records in
this log, the Feature Complete Manual Audit, and the Charter were left
untouched.

## Public Portfolio Delivery — Version / Delivery Decision resolved

The repository owner made the previously pending Version / Delivery
Decision recorded at the Release Candidate Gate: current version `0.10.0`
is approved for public portfolio delivery, and the GitHub repository
visibility is now public. No version tag or GitHub Release was created as
part of this decision, and none is implied by it; a formal tagged release
remains a separate, independent decision the repository owner has not made.

Updated `PROJECT_STATUS.md`, `ROADMAP.md`, and `README.md` to record the
current lifecycle phase as Public Portfolio Delivery instead of Release
Candidate, and updated the hardcoded current-phase assertions in
`tests/test_lifecycle_consistency.py` accordingly (the former Release
Candidate phase strings were added to that test's stale-phrase blocklist,
following the same pattern used at every earlier lifecycle transition).
This is a governance/documentation-only closure: no product code, product
behavior, test behavior beyond the lifecycle-phase assertions themselves,
database/schema, or release version changed. Earlier gate records in this
log and in `PROJECT_STATUS.md` describing the prior "no release decision
yet" state were left untouched, since they were accurate at the time they
were written.

## Release Candidate Gate — PASS

Executed the Release Candidate milestone against candidate SHA
`427984a5d39b7e20eafc53e588aa5a53b6bd320d` (PR #31 merged; independent
post-merge `main` CI PASS on 3.11/3.12/3.13). First confirmed
`71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1..427984a5d39b7e20eafc53e588aa5a53b6bd320d`
touches only six governance/docs/lifecycle-test files, so the 2026-08-14
Full Regression and Manual Acceptance evidence (20/20 required items PASS,
0 blocking defects, all nine carried-forward FCRs VERIFIED) remains valid
runtime evidence and was not re-executed.

Built the actual installable wheel from a clean detached worktree at the
candidate SHA (`git worktree add`, `python -m build --wheel`) rather than
building from the working tree, and inspected it directly rather than
assuming: `social_text_intelligence-0.10.0-py3-none-any.whl` contains all
13 templates, 5 static files, and 4 packaged JSON resources plus `LICENSE`,
and nothing else (no tests, caches, weights, or private data). `METADATA`
and `entry_points.txt` confirm `social-text-intelligence` `0.10.0`,
`Requires-Python >=3.11`, `sti`/`sti-web` console scripts, and the
`sentiment`/`emotion`/`web`/`dev` extras with correct constraints.

Ran two clean-install smokes in fresh temporary venvs, not the working
`.venv`: a no-extras core install (`pip check` clean, installed version
`0.10.0`, `sti about` and `sti contracts` both work) and a `[web]`-extra
install (`sti-web --help` works; the server bound to `127.0.0.1` only,
confirmed via `netstat` rather than assumed from source; the installed
wheel's home page and `/static/app.css` both returned 200, proving
templates/static were genuinely packaged, not just declared). With no
model extras installed, POSTing a Direct analysis returned HTTP 200 with
an honest in-page error ("Local model dependencies are not installed.
Install the model extras.", `role="alert"`) rather than a crash or
misleading partial success — verified live, not assumed from the RC
prompt's expectation.

Reconciled model pins (`cardiffnlp/twitter-roberta-base-sentiment-latest@
3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`,
`SamLowe/roberta-base-go_emotions@d75048347613a25d77de8cf6412eaae9fa7b26be`)
against the candidate source directly rather than trusting memory: both
match exactly and are passed as explicit non-floating `revision=`
arguments. Reconciled `LICENSE`/`THIRD_PARTY_NOTICES.md`/`pyproject.toml`
against the built wheel's `METADATA`: mutually consistent, no
redistribution-of-weights claim contradicted. Confirmed `.gitignore`
protects `dist/`/`build/`/`model_cache/`/`manual-qa/results/`, confirmed
`.prompt-drafts/` is excluded via `.git/info/exclude` and untracked, and
found no bundled weights/databases/credentials/secrets in either tracked
files or the built wheel.

No release blocker was found; no RC-scoped correction was necessary.
**Release Candidate Gate: PASS.** Updated `PROJECT_STATUS.md`, `ROADMAP.md`,
`README.md`, and `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md` (new dated PASS
decision, bilingual) to record the result. Did not bump the version to
`1.0.0`, did not create a tag or GitHub Release, and did not set release
readiness to Yes — the next required action is an explicit Version /
Delivery Decision by the repository owner. No product code, template,
route, or model behavior was touched.

## PR #31 corrective governance patch — carried-forward FCR reconciliation

Formal review of PR #31 found that its Full Regression and Manual
Acceptance PASS decision directly resolved FCR-003 but left the other eight
Roadmap-required carried-forward pre-freeze `OPEN verification` items
(FCR-005, 014, 015, 017, 021, 023, 026, 031) unresolved and moved them into
Release Candidate, while also silently dropping the Roadmap requirement
that this phase close or formally dispose of them. That both weakened the
completed phase's acceptance criteria retrospectively and left the gate's
closure condition unmet, since the Roadmap had explicitly carried these
nine items into this phase for disposition, not the next one.

This is a governance/evidence adjudication correction, not a request to
repeat manual testing: no product code, template, route, model, filter,
sort, or questionnaire content changed. For each of the eight remaining
FCRs, read the full permanent record and located the strongest existing
evidence rather than performing a fresh audit or rerunning interactive
scenarios:

- **FCR-005** (native/compact, multi-label threshold, neutral semantics):
  already-VERIFIED FCR-034 plus
  `tests/test_web_app.py::test_post_renders_complete_combined_report` and
  `::test_neutral_result_explains_threshold_fallback`.
- **FCR-014** (Insights raw counts/denominators/sample warnings/
  perspectives): four dedicated tests in `tests/test_insights_service.py`,
  one per sub-question.
- **FCR-015** (Context Note authorship/UTC/deletion/non-label semantics):
  already-VERIFIED FCR-038 plus
  `test_context_notes_are_separate_validated_and_deletable` plus the
  `insights.html` template's explicit "user-authored," "Manual annotation
  only," and "not protected-attribute labels" copy.
- **FCR-017** (Moderation policy/provenance/mock honesty):
  `tests/test_moderation_resources.py`'s two provenance tests plus this
  session's own live observation of the Prepare page (Scenario D).
- **FCR-021** (Triage guide/ticket provenance, draft, no-mock states):
  three dedicated `tests/test_triage_routes.py` /
  `tests/test_support_triage.py` tests plus this session's own live
  observation of Source & Guide / Workspace (Scenario E).
- **FCR-023** (Triage mock visibility/exclusion/denominators): five
  dedicated tests split across `tests/test_support_triage.py` and
  `tests/test_triage_routes.py`, one per sub-question.
- **FCR-026** (formula-injection escaping): this session's own Scenario C
  (`review-formula`, one of the 20 required profile items) plus the
  five-export-path code re-check already recorded in the 2026-08-14 Product
  Hardening closure decision.
- **FCR-031** (current-version scope completeness): a scope/judgment item,
  not a behavioral defect — resolved by the 2026-08-13 Feature Freeze
  decision's explicit "Open current-version blockers: None," the existing
  FCR disposition map's `VERIFIED / Keep as-is` marks on every individual
  current-version capability question, and Product Hardening A1-A10's
  explicit no-scope-expansion constraint honored throughout.

All nine carried-forward FCRs (including the already-resolved FCR-003) are
now closed `VERIFIED` in a single reconciliation embedded in the Full
Regression and Manual Acceptance PASS decision in
`docs/FEATURE_COMPLETE_MANUAL_AUDIT.md` (both languages), with the
Section 4 checklist table and the disposition-map bullet list updated to
match. Restored the Roadmap's original requirement text that this phase
close or formally dispose of these nine items, now marked satisfied, rather
than leaving it silently removed. Updated `PROJECT_STATUS.md`'s "Open
blockers" and "Approved audit items" rows accordingly. The gate result is
unchanged: Full Regression and Manual Acceptance remains PASS (20/20
required fresh-interaction items, 0 FAIL, 0 blocking defects), and the
current lifecycle phase remains Release Candidate (not started). No new
manual interaction was required beyond what the 2026-08-14 session had
already gathered.

## Full Regression and Manual Acceptance — PASS

Repository-owner-authorized agent-operated session executed Full Regression
and Manual Acceptance against tested SHA
`71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1` (PR #30 merged; independent
post-merge `main` CI PASS on Python 3.11/3.12/3.13). Automated Full
Regression evidence reused that exact-SHA CI rather than re-running pytest/
Ruff/MyPy/compile locally, per explicit cost-minimization instructions, plus
existing Product Hardening real-model/concurrency/HTTP-boundary/
browser-security evidence.

Manual Acceptance used a repository-owner-defined minimum required
fresh-interaction profile of 20 questionnaire IDs, executed as six
consolidated scenarios in a real offline `sti-web` server (real pinned
models) and a real browser rather than 20 separate procedures:

- **A (Startup + Direct):** app launch, all four top-level routes, visible
  privacy/English-only/non-diagnostic boundaries, blank-input rejection, and
  a genuine server-side over-length rejection (21999 chars, client
  `maxlength` bypassed) with no truncation or stack trace.
- **B (Batch edge workflow):** one 9-row edge-case CSV through preview (3
  valid / 6 invalid, each error typed correctly), a captured `aria-busy`/
  disabled-button/`role=status` running state during analysis, completed
  analysis (2 analyzed / 7 failed, including a correct
  `unsupported_language` failure for the French row), and an explicit
  clear with confirmed cleared-token recovery.
- **C (Review formula export):** `=SYNTHETIC_FORMULA_TEST` in a review note
  exported with a safe apostrophe prefix.
- **D (Moderation structural/warning pair):** a submission with
  `reasoning`/`reviewer_note` required-attributes bypassed was rejected
  server-side with no partial save; a structurally valid `allow` +
  `harassment_abuse` + `severity=none` submission was saved with retained,
  non-rewriting guidance warnings.
- **E (A9/A10 state integrity):** a 4-row synthetic batch purpose-built for
  the sort contract (aware `+05:00`, aware `-05:00` with lexical order
  reversed from real-instant order, a timezone-unspecified row, and a
  missing-timestamp row) linked into Triage and sorted by Timestamp
  rendered exactly aware-by-instant, then naive, then missing — confirmed
  by opening each ticket, not by trusting row position alone.
  `cross-applied-state` was verified on all three required surfaces (Triage
  Workspace, Moderation Prepare, Insights Representative Cases) with a
  non-default query state reflected correctly on reload.
- **F (cross-cutting):** the real skip-link was the first Tab stop and
  moved focus to `<main>` on activation; the active nav link carried
  `aria-current="page"`; a validation failure set `aria-invalid`,
  `aria-describedby`, `autofocus`, and `role="alert"`; the full session's
  Werkzeug access log was reviewed and contains no submitted text or PII;
  a CSV export response carried `Cache-Control: no-store` and a strict CSP/
  security-header set; and clearing a Batch workspace proved immediate
  process-memory loss with a clean, non-crashing recovery message on the
  cleared token.

Result: 20/20 PASS, 0 FAIL, 0 blocking defects. FCR-042/FCR-043 untouched.
FCR-003 was directly exercised by `direct-limits` and found consistent with
current-version product behavior (Direct enforces only length and
English-only; the unsupported-language-tag case belongs to Batch). The
remaining eight carried-forward pre-freeze items (FCR-005, 014, 015, 017,
021, 023, 026, 031) were reconciled against existing evidence in the same
decision and closed `VERIFIED` — see the corrective governance patch below,
which closes all nine before advancing to Release Candidate. Evidence
exported to
`manual-qa/results/sti-full-regression-manual-acceptance-71fa608-2026-08-14.{json,md}`
(local-only, gitignored).

Updated `PROJECT_STATUS.md`, `ROADMAP.md`, `README.md`, and
`docs/FEATURE_COMPLETE_MANUAL_AUDIT.md` (new dated PASS decision, bilingual)
to record the PASS and advance the current lifecycle phase to Release
Candidate (not started). Updated `tests/test_lifecycle_consistency.py`'s
hardcoded phase/status assertions to match. No product code, template, or
route was touched.

## PR #30 corrective patch — FCR-003 Direct acceptance alignment

Formal readiness review of PR #30 found that the newly added `direct-limits`
questionnaire item claimed Direct analysis clearly rejects "an unsupported
language tag," but Direct exposes only a text field: it declares "English
only," has no language-selection control, and constructs
`NormalizedTextInput` with a hardcoded `language="en"` internally
(`src/social_text_intelligence/interface/app.py`). There is no reachable
interaction on Direct through which a reviewer could submit a language tag
for the product to reject, so the item described a test that cannot
actually be performed against the current-version product.

Re-read the full FCR-003 permanent record: it remains a carried-forward
pre-freeze `OPEN verification` item asking whether blank, oversized,
English, and unsupported-language outcomes are recoverable, evaluated across
the product rather than mandating that every one of those cases be
reachable specifically through Direct. Nothing in the record requires
Direct to gain a language control, and no product code was changed.

This is an acceptance-artifact-only correction. `direct-limits` now checks
only what Direct actually enforces: the application text-length limit is
rejected before inference with no silent truncation, and the English-only
boundary is honestly stated on the page. The unsupported-language-tag case
remains covered — through Batch's `language` CSV column, exercised by the
existing `batch-edge-preview` item — and the corrected `direct-limits` item
text says so explicitly rather than silently dropping the language half of
FCR-003's audit topic. `direct-validation` (blank input) is unchanged.
Corrected the matching description in this file's own prior entry below.
Gate Standard, questionnaire v3.0/schema compatibility, English
completeness, all other new items, current lifecycle phase/status, and
FCR-042/FCR-043 dispositions are untouched.

## Full Regression and Manual Acceptance — readiness preparation

Readiness preparation only: establishes the acceptance standard and upgrades
the canonical questionnaire so a future authorized session can execute Full
Regression and Manual Acceptance without re-deriving either. Does not execute
that phase, does not change product behavior, and does not change Manual
Acceptance status (Not started), Release Candidate status (Not started), or
release readiness (No).

Added `docs/MANUAL_ACCEPTANCE_GATE.md`, the permanent acceptance contract:
PASS conditions, a blocking definition (correctness, data/state integrity,
privacy/security, critical-workflow completion, user-controlled-output
loss, materially misleading state, required accessibility/recovery paths,
or a reproducible crash/dead end — explicitly excluding pure cosmetic
findings), N/A rules requiring a stated reason, evidence expectations, a
Fix → Retest workflow, and an explicit executor model: an authorized
interactive coding agent may execute Manual Acceptance by operating the
real application and a real browser, judging results through genuine
interaction/DOM/browser state, and never marking PASS from source-code
reasoning alone. The two evidence streams — automated Full Regression and
interactive Manual Acceptance — are named as jointly required; neither
alone is sufficient.

Upgraded `manual-qa/manual_review_questionnaire.html` (questionnaireVersion
2.0 -> 3.0; schemaVersion left at 2.0 so existing exported JSON still
imports). Reframed the hero eyebrow/copy from "Feature Complete Review" to
"Full Regression & Manual Acceptance · 0.10.0," added a rendered Acceptance
Gate Standard panel (PASS/blocking/N/A/evidence/executor summaries, fully
bilingual), relabeled the na status to make its N/A-and-not-tested meaning
explicit, and adjusted the historical Feature Freeze and Product Hardening
sections to read as retrospective confirmation rather than upcoming work
now that both are closed.

Reconciled checklist coverage against the final 0.10.0 product and the
A1-A10 hardening contracts rather than assuming gaps. Five items were
genuinely missing and added: `triage-timestamp-sort` (FCR-051 aware/
timezone-unspecified/missing ordering), `cross-applied-state` (FCR-052
filter/sort/selection reflection across Triage Workspace, Moderation
Prepare, and Insights Representative Cases), `cross-a11y-semantics` and
`batch-busy-state` (FCR-027/A8 skip-link, current-step, focus-recovery, and
Batch busy-state semantics that predate the original questionnaire), and
`direct-limits` (FCR-003's over-length case for Direct analysis, which
existing coverage did not exercise). One
existing item (`direct-multilabel`) gained a clause for FCR-034's neutral
threshold-fallback semantics rather than a new item. All other requested
categories — privacy defaults, no-store/local boundaries,
formula-injection-safe export, partial Batch failures, threshold
boundaries, expiry/recovery, and the remaining carried-forward pre-freeze
items (FCR-014, 015, 017, 021, 023, 026, 031) — already had sufficient
existing coverage and were left untouched; formula-injection protection in
particular is a single shared `safe_spreadsheet_text()` function already
exercised once via `review-formula`, so a duplicate check per export
surface was not added.

Verified live in a real browser rather than by code reading alone: the page
loads and both languages render with identical key sets (62/62, checked
programmatically); marking items updates progress/pass/fail/na counts;
JSON export round-trips through the real `importJson()` file-input path
including a language switch on import; a simulated pre-upgrade export
(schemaVersion 2.0, old item set) still imports cleanly with new items left
unanswered rather than erroring; Markdown export includes the new items.
Confirmed the questionnaire's pre-existing narrow-width horizontal overflow
(present identically on unmodified `main`) is unrelated to this change and
out of this readiness-prep scope.

Also updated `PROJECT_STATUS.md`, `ROADMAP.md`, `docs/DEVELOPMENT.md`,
`README.md`, and `manual-qa/README.md` to point to the new standard, without
touching FCR-042/043 dispositions, release readiness, or any filtering/
sorting/model behavior.

## Product Hardening closure — entering Full Regression and Manual Acceptance

Product Hardening Batch A10 / PR #28 is recorded as merged to main at SHA
`fc230c587c245cdb1cd75b399c91eb38ac82d768`; independent post-merge `main` CI
passed on Python 3.11, 3.12, and 3.13.

Taking that SHA as baseline, a read-only lifecycle audit reconciled
`PROJECT_STATUS.md`, `ROADMAP.md`, `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`,
and `DEVLOG.md` against the permanent FCR ledger rather than trusting only
the summary rows. Ten batches (A1-A10) closed ten permanent findings
(FCR-027, FCR-030, FCR-045-052), all `VERIFIED`. Every approved Phase 0
finding is closed: PH-001-PH-002 under FCR-045, PH-003 under FCR-046, PH-004
under FCR-047, PH-005 under FCR-048, PH-006 under FCR-049, PH-007 under
FCR-050, PH-008 under FCR-030, PH-009 under FCR-027, and PH-010 under
FCR-051. FCR-052 is a separately discovered, closed, non-blocking finding
outside the original PH-001-010 list.

FCR-042 (score-list ordering) and FCR-043 (explanatory/error visual
hierarchy) were re-read in full rather than assumed. Both permanent records
already state no correctness, safety, privacy, or data risk: FCR-042 is
readability-only and does not touch values, labels, or auditability, and
FCR-043 describes text that is already visible and recoverable, only lacking
strong visual weight differentiation. Neither materially prevents Full
Regression and Manual Acceptance, so neither was implemented and neither was
marked VERIFIED or CLOSED; both remain explicit `OPEN` non-blocking backlog.

The remaining nine "OPEN verification" items from the initial audit checklist
(FCR-003, 005, 014, 015, 017, 021, 023, 026, 031) predate Product Hardening
entirely — they were already unresolved when Feature Freeze passed on
2026-08-13. FCR-026 (formula-injection protection), the one with the
clearest potential severity, was directly re-checked against current code:
`safe_spreadsheet_text()` is applied to every export field across Batch,
Review, Insights, Moderation, and Triage, each with its own dedicated
regression test proving the `=`/`+`/`-`/`@` escaping behavior. No defect was
found in any of the nine. They are formally carried into Full Regression and
Manual Acceptance for disposition, matching that phase's own defined job in
`ROADMAP.md`, rather than being treated as Product Hardening blockers or
triggering a speculative new hardening batch to manufacture an A11.

With no known material blocker remaining, Product Hardening closes
`COMPLETE`. `PROJECT_STATUS.md`, `ROADMAP.md`, `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`
(both language sections, plus a new dated closure-decision block mirroring
the existing Feature Freeze decision format), and `README.md` are updated
together so the current phase reads consistently everywhere. Current
lifecycle phase becomes Full Regression and Manual Acceptance. This is not a
claim that Manual Acceptance has passed, that a Release Candidate has
started, or that release readiness has changed from No — those remain
separate, later gates. No product code changed.

## Product Hardening Batch A10 — Applied filter/sort/selection state reflection integrity

Product Hardening Batch A9 / PR #27 is recorded as merged to main at SHA
`3fecf5ce43939045ed7100915eca41b9e5b2c64e`; FCR-051 remains `VERIFIED`.

A read-only audit of every GET filter/sort form in the interface (Triage
Workspace and Guide, Review, Batch, both Insights view forms, Moderation
Prepare) found that Review, Batch, the Insights explorer view, and Triage
Guide's built-in ticket filter already reflected applied query state
correctly, while three surfaces did not: Triage Workspace's 11 select
controls and its `q` text-search input, Moderation Prepare's 5 select
controls (whose route did not even pass the parsed filters into the
template), and Insights Representative Cases' `record_id` checkboxes,
which genuinely determine the result in `user_selected` mode but were
never checked. None of this is covered by FCR-027 (keyboard/accessibility
semantics, already `VERIFIED` with an explicitly narrower scope), FCR-029
(error/empty-state recovery — nothing here errors), or FCR-030
(documentation consistency, not runtime UI), and it is not folded into
FCR-042 or FCR-043. New permanent `FCR-052` is created, classified
`HARDENING`, non-blocking.

All three surfaces now use the same native Jinja `selected`/`checked`/
`value` pattern already proven correct elsewhere in the codebase. Moderation
Prepare's route passes its existing `CaseFilter` into the template instead
of building a second parser. Insights checkbox reflection is deliberately
gated to `example_mode is ExampleMode.USER_SELECTED`, since `record_id` has
no effect in any other mode and reflecting it unconditionally would falsely
imply a stale, non-effective query parameter was still driving the result.
No filtering, sorting, or selection logic changed, and the FCR-051 timestamp
sort algorithm is untouched.

Fourteen targeted regressions cover: enum/boolean/text-search filters that
narrow the Triage result while the matching control shows `selected`/
`value`; the default no-query view showing no unexpected non-default state;
Moderation difficulty and tri-state safety-sensitive filters narrowing the
built-in case library while reflecting correctly, including a combined
non-default case; Insights `user_selected` mode checking exactly the
submitted records and excluding others; and a non-selecting example mode
correctly leaving `record_id` unchecked, proving the effective-state gate.
Eleven of the fourteen fail against the pre-fix implementation. The complete
suite passed 195 tests (14 more than the A9 baseline) with 2 opt-in model
integrations skipped; Ruff, strict MyPy for 75 files, compileall, and pip
check passed, and the 9 FCR-051 targeted regressions were unaffected.

A real-browser smoke drove the actual Triage workspace-creation, ticket,
Moderation workspace-creation, and Batch-to-Insights paths. Applying
`status=finalized` and `sort=urgency` in Triage Workspace left only the
finalized ticket visible with both controls genuinely selected. Applying
`difficulty=beginner` and `safety_sensitive=false` in Moderation Prepare
narrowed the case library to exactly the three matching built-in cases with
both controls genuinely selected. Selecting two records in Insights
Representative Cases under `user_selected` mode left exactly those two
checkboxes checked after submission. Behavioral candidate:
`c1feb67e1b40742c7f34104e5f0922d67498dd12`. FCR-052 is `IMPLEMENTED` pending
PR review. FCR-042 and FCR-043 remain open non-blocking, and Feature Freeze
remains PASS.

PR #28 formal review subsequently passed on reviewed head
`6c649dc78c18921937a2d6b49e52a94cc7e92d94`, which also passed final-head CI
on Python 3.11, 3.12, and 3.13. FCR-052 is therefore `VERIFIED`. FCR-051
remains `VERIFIED`, Feature Freeze remains PASS, and FCR-042/043 remain
`OPEN` non-blocking.

## Product Hardening Batch A9 — Triage timestamp ordering integrity

Reconciled Phase 0 PH-010 as new permanent `FCR-051`. Existing FCR-015 and
FCR-038 govern Context Note UTC display, FCR-042 governs score-list ordering,
and FCR-043 governs visual hierarchy; none defines the timestamp-ordering root
cause, so a new permanent ID was created rather than stretching an existing
one. The post-A8 governance sync PR #26 is recorded as merged at main SHA
`7ef4d29d2bb98af2a60003748a575de8c5bcda96`, the baseline for this batch.

The Support Triage `Sort: Timestamp` control sorted the stored ISO timestamp as
a raw string. Batch CSV accepts any valid ISO 8601 value and keeps its stated
offset (or its unspecified-timezone status) rather than normalizing it, so one
workspace can hold several offsets at once, and lexicographic order is not
real-instant order: `2026-07-01T08:00:00-05:00` is 13:00Z but sorts as text
before `2026-07-01T10:00:00+00:00`, which is 10:00Z. The wrong order was
silent, and the branch had no test coverage.

Ordering now parses the value and applies one explicit contract. Offset-aware
timestamps sort first, ascending by real instant. Timezone-unspecified values
are never assigned a zone; they form a separate later bucket ordered by stated
wall-clock value. Missing or unparsable values sort last. `original_order`
breaks every tie, and because the leading bucket always differs, values from
different buckets are never compared with each other. Aware values keep their
original offset and rely on native instant comparison instead of
`astimezone(UTC)`, which raises `OverflowError` on parsable extremes such as
`9999-12-31T23:59:59-14:00` and would otherwise crash the page.

Nothing about timestamp truth changed. The accepted Batch input range,
`NormalizedTextInput.timestamp`, Review display, Triage trusted metadata, the
Batch/Insights/Triage export representation, and system-generated UTC audit
timestamps are all untouched, and user timestamps are still never normalized to
UTC. `docs/CONTRACTS.md` now states the sort contract, the boundary between
user timestamps and system audit timestamps, and the unchanged Insights
month/date grouping semantics. The workspace sort control carries associated
help text so the interface does not imply that timezone-unspecified and
offset-aware values share one timeline.

Nine targeted regressions cover instant-versus-string ordering, the stable
tie-break for one instant spelled with two offsets, naive wall-clock ordering,
the mixed-bucket contract, missing-last ordering, extreme-offset safety,
non-interference with the other sort modes, and preservation of stored values.
Five of them fail against the pre-fix implementation, and the extreme-offset
case fails against an `astimezone` variant. The complete suite passed 181 tests
with 2 opt-in model integrations skipped; Ruff, strict MyPy for 74 files,
compileall, and pip check passed.

A real-browser smoke drove the actual Batch upload, analysis, workspace-ticket,
and `Sort: Timestamp` path with a synthetic batch holding two different
offsets, one timezone-unspecified timestamp, and one missing timestamp. The
rendered order was 10:00Z, 13:00Z, timezone-unspecified 1999, then missing; the
other sort modes were unaffected; and every stored timestamp remained its
original text with no conversion. Behavioral candidate:
`076fbe4f883073a1961b024d52d06d9cac22a58a`. FCR-051 is `IMPLEMENTED` pending
PR review. FCR-042 and FCR-043 remain open non-blocking, and Feature Freeze
remains PASS.

PR #27 formal review subsequently passed on reviewed head
`ef9b54adc3eeed98ef4154f71ae7f69e5f6000cb`, which also passed final-head CI on
Python 3.11, 3.12, and 3.13. FCR-051 is therefore `VERIFIED` and PH-010 is
closed; FCR-027, FCR-030, and FCR-045–050 remain `VERIFIED`, Feature Freeze
remains PASS, FCR-042/043 remain `OPEN` non-blocking, and the parked
filter/select applied-state finding remains a separate, unresolved item outside
FCR-051.

## Product Hardening Batch A8 — accessibility semantics and keyboard recovery

Reconciled Phase 0 PH-009 with existing FCR-027 rather than creating FCR-051.
The 2026-08-13 `VERIFIED / Keep as-is` keyboard smoke remains historical
evidence. A deeper Product Hardening audit found material semantic gaps, so
FCR-027 is revalidated as class `HARDENING`, decision `Keep and harden`, status
`IMPLEMENTED` pending PR review and final manual keyboard smoke. Product
Hardening Batch A7 / PR #24 is recorded as merged at main SHA
`e73ed30c54b78630fd9bae7193119868277ca70a`; FCR-030 remains `VERIFIED` and
Feature Freeze remains PASS.

Every complete server-rendered page now provides a visible-on-focus skip link
to a focusable main landmark. Active primary navigation and workflow steps use
`aria-current`; Direct validation associates its alert and help with the text
field and restores focus there, while workflow-level errors restore focus to a
focusable alert. Key helper text is programmatically associated with Batch,
Review, Insights, Moderation, and Triage controls. Batch analysis publishes a
labelled progress status and sets `aria-busy` during submission. Representative
data tables now declare column and row header scope. Native controls remain in
place, summary joins the existing visible-focus rule, and no positive tabindex,
faux button, dependency, workflow redesign, or CSP relaxation was introduced.

Six focused accessibility regressions cover skip targets, current-page/step
semantics, labels/help/errors, focus-recovery markup, Batch running state,
explicit table headers, and keyboard anti-pattern scans. The complete suite
passed 172 tests with 2 opt-in model integrations skipped. Ruff, strict MyPy for
73 files, compileall, pip check, CSP/security regressions, static checks, and
repository privacy/safety checks passed.

Real-browser smoke passed Direct validation focus recovery and real-model
success, Batch preview/analysis, Human Review acceptance, Insights navigation,
note creation, and note-error focus recovery. The local browser-control
security boundary interrupted the remaining Moderation/Triage browser session;
those final keyboard-only flows remain explicitly assigned to user retest.
Behavioral candidate: `577bb3d09cb02eeebc36133cd5ce408d5fae4a20`.
FCR-043 remains open for visual information hierarchy, and PH-010 is not
started.

The user's final keyboard-only smoke subsequently passed for Moderation and
Support Triage, with no keyboard trap, a visible focus indicator, and
recoverable validation errors. Reviewed PR #25 head
`41bd13118b77b1c35a58f72f9bd68189afc04df3` passed CI on Python 3.11, 3.12, and
3.13. FCR-027 is therefore `VERIFIED` and PH-009 is closed; FCR-030 and
FCR-045–050 remain `VERIFIED`, Feature Freeze remains PASS, FCR-043 remains
`OPEN` non-blocking, and PH-010 remains unstarted and unscoped. PR #25 merged
to main at `75c323bb998f47262dfbd8f69ab90bf1998e92fa`.

## Product Hardening Batch A7 — lifecycle and CLI consistency

Reconciled Phase 0 PH-008 with existing FCR-030 rather than creating a second
permanent finding. FCR-030 is classified `HARDENING`, decision `Keep and
harden`, and remains `IMPLEMENTED` pending PR review. Product Hardening Batch
A6 / PR #23 is recorded as merged at main SHA
`cfcd13ef582996b8c75aa20524dcc212e2ab8922`; FCR-050 remains `VERIFIED` and
Feature Freeze remains PASS.

Separated current-state responsibilities to prevent recurring drift:
`PROJECT_STATUS.md` is the only canonical live execution state, `ROADMAP.md`
owns the mutable lifecycle plan, `PROJECT_CHARTER.md` owns stable product and
engineering boundaries, `README.md` provides a concise current overview, and
`docs/DEVELOPMENT.md` defines contributor discipline. Current references now
agree on version 0.10.0, Milestones 1–10 complete, Feature Complete Review
Completed, Feature Freeze PASS, Product Hardening current, Manual Acceptance
and Release Candidate not started, and release readiness No. The canonical
Manual QA link remains `manual-qa/manual_review_questionnaire.html`.

`sti about` now reports the installed version, Milestone 10 feature boundary,
and existing capabilities. It deliberately does not embed the live phase,
gate, PR, SHA, blocker, or release-readiness ledger; instead it points users to
the repository `PROJECT_STATUS.md`. Targeted regression rejects the former
feature-freeze-pending statement and prevents the CLI from duplicating current
lifecycle values.

The stale-state audit changed only current declarations and instructions.
Dated handoffs, DEVLOG entries, historical FCR evidence, and past PR records
retain statements that were accurate at the time. No model, threshold,
workflow, state, security, privacy, product-scope, or version contract changed.
PH-009 remains unstarted.

Ten focused CLI/lifecycle tests passed. The complete deterministic suite passed
167 tests with 2 opt-in model integrations skipped. Ruff, strict MyPy for 72
files, compileall, pip check, tracked-document stale-state/link/manual-QA
consistency checks, and repository privacy/safety checks passed. Behavioral
candidate `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` passed lifecycle/CLI
consistency review. Reviewed PR #24 head
`371b41bec0c6418bc07748a36d34e46dd4392664` passed final-head CI on Python
3.11, 3.12, and 3.13. FCR-030 is therefore `VERIFIED`; FCR-045–050 remain
`VERIFIED`, Feature Freeze remains PASS, and PH-009 remains unstarted. This
closure changes governance documentation only.

## Product Hardening Batch A6 — Local browser boundary hardening

Reconciled Phase 0 PH-007 as permanent FCR-050. Existing FCR-045–049 govern
ephemeral capacity/state, complete-input inference, request-body capacity,
real-model evidence, and concurrent mutations; none defines the browser Host,
same-origin, or response-header boundary.

Behavioral candidate `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`
passed Host/same-origin/CSP/security-header code review and PR #23
behavioral-head CI on Python 3.11, 3.12, and 3.13. The user also completed a
real-browser smoke: Direct, Batch/Review, Insights distribution progress and
notes, Moderation/Triage forms, and CSV downloads operated normally, with no CSP
violation or blocked local resource in DevTools Console. FCR-050 is therefore
`VERIFIED`. This closure changes governance documentation only; FCR-049 remains
`VERIFIED`, Feature Freeze remains PASS, and no later hardening item is started.

Configured Flask trusted hosts for exactly `127.0.0.1` and `localhost`, while
the CLI continues binding only `127.0.0.1`. A fixed private 400 handles rejected
Host values before route dispatch. Unsafe methods now require an exact
same-origin Origin, or a same-origin Referer when Origin is absent; explicit
cross-origin, malformed, or `null` values receive a fixed private 403. Requests
with neither header remain supported as documented local non-browser clients
behind trusted Host validation. Rejection occurs before model inference,
request-body parsing, or workspace mutation.

All responses now receive a self-only CSP, `nosniff`,
`Referrer-Policy: same-origin`, `X-Frame-Options: DENY`, and the existing
no-store/no-cache headers. The CSP uses no wildcard, external origin, or
`unsafe-inline`. Replaced the sole dynamic inline style in Insights with a
native progress element styled by the existing local stylesheet. HSTS, CORS,
TLS, LAN binding, sessions, accounts, remote deployment, and CSP reporting are
explicitly excluded.

Focused regressions cover approved hosts, same-origin and fallback behavior,
private Host/Origin rejection before inference, preservation of Batch/Review/
Insights/Moderation/Triage state, headers on HTML/redirect/error/413/CSV/static
responses, and the absence of inline/external template resources. Selected A3
request-ceiling and A5 lease/concurrency tests remain green. Feature Freeze
remains PASS; no later PH item is started.

Twelve focused browser-boundary/A3/A5 tests passed. The complete deterministic
suite passed 163 tests with 2 opt-in model integrations skipped. Ruff, strict
MyPy for 71 files, compileall, and pip check passed.

Batch A5 / PR #22 was merged at main SHA
`3a0bb9c9460379b55a6488f966034419e40cf91d`, the synchronized A6 baseline;
FCR-049 remains `VERIFIED`.

## Product Hardening Batch A5 — Concurrent workspace mutation integrity

Reconciled Phase 0 PH-006 as permanent FCR-049. FCR-045 protects Batch
capacity, TTL, and active-analysis write-back, but it does not cover stale
read/derive/replace races across the broader process-memory workspace stores.

Behavioral candidate `a3ec11b674c11148d66be73475b43d0796329a54`
passed current-state mutation/concurrency integrity code review and PR #22
behavioral-head CI on Python 3.11, 3.12, and 3.13. FCR-049 is therefore
`VERIFIED`. This closure changes governance documentation only; FCR-048 remains
`VERIFIED`, Feature Freeze remains PASS, and PH-007 is not started.

Added one shared store-level atomic mutation primitive. Batch, Moderation, and
Triage stores now invoke each mutation against the current workspace while the
store lock is held, then save that result atomically. Independent mutations
therefore compose instead of replacing one another from stale snapshots.
One-shot rules are revalidated against current state: competing Moderation
first decisions and Triage finalization return an explicit HTTP 409 instead of
silently overwriting an accepted decision. Missing or expired workspaces retain
404 semantics, and Batch active-analysis mutations remain blocked by the A1
lease contract.

Protected mutations include Batch column selection; Human Review decisions;
persisted Insight selections and context-note add/delete; Moderation prepared
cases, sessions, decisions, feedback, cancellation, and restart; and Triage
ticket addition, draft, finalize, revise, and mock reveal. Render-only GET
navigation, filters, summaries, exports, and request-local presentation choices
remain transient because they do not replace persisted workspace state.

Deterministic nested interleaving regressions verify final saved state for
independent Review rows, Review plus Insight note, two notes, Moderation cases,
competing first decisions, separate Triage tickets, competing finalize, expiry,
and the active Batch lease. Feature Freeze remains PASS; PH-007 is not started.

Nine focused concurrency/state tests passed. The complete deterministic suite
passed 157 tests with 2 opt-in model integration tests skipped. Ruff, strict
MyPy for 70 files, compileall, and pip check passed.

Batch A4 / PR #21 was merged at main SHA
`5778f8f8804c3014f16940af1d7254c202dbcf41`, the synchronized A5 baseline;
FCR-048 remains `VERIFIED`.

## Product Hardening Batch A4 — Real-model capacity evidence

Reconciled Phase 0 PH-005 as permanent FCR-048. FCR-045 governs Batch capacity,
TTL, and active-analysis state integrity, while FCR-046 governs complete-input
inference truthfulness; neither supplied measured release evidence for the
pinned models at the 500-row product ceiling.

Added an explicit opt-in benchmark harness outside ordinary CI. It forces
offline mode, uses the existing local cache, and runs the production
`AnalysisService`, sequential `analyze_batch`, and `EphemeralBatchStore`
lease/write-back path with eight deterministic, synthetic English templates.
It records environment, cold initialization, first combined inference, warm
1/50/500-row timing and throughput, success/failure counts, process RSS, and
whether an active workspace survives and commits beyond an artificial 1-second
TTL. No `src/` product behavior, model, revision, threshold, limit, provider,
workflow, persistence, or runtime architecture changed.

On the 2026-08-14 UTC reference run (Windows 11, Python 3.12.13, Intel
i7-12700H, approximately 16 GB RAM, PyTorch 2.13 CPU-only), offline model
initialization through the first result took 3.626 seconds. Warm 1/50/500 rows
took 0.075/3.763/39.636 seconds; the 500-row stage achieved 12.61 rows/second,
with 500 successes and zero failures. Peak process RSS was 1,061,908,480 bytes
(about 0.99 GiB), while post-load growth through 500 rows was about 2.97 MiB.
The 50- and 500-row stages both exceeded the probe TTL, retained their active
lease, and committed successfully.

The evidence supports retaining `MAX_BATCH_ROWS=500` for the explicit local
synchronous workflow, with a reproducible reference RC budget documented in
`docs/REAL_MODEL_CAPACITY_EVIDENCE.md`. The budget is scoped to the checked-in
short social-text fixture and comparable CPU desktop, not presented as a
universal latency SLA. FCR-048 and PH-005 are therefore `VERIFIED`; corrective
product work is not required. Feature Freeze remains PASS, and PH-006 is not
started.

The full deterministic suite passed 148 tests with 2 opt-in integration tests
skipped. Ruff, strict MyPy for 69 files, compileall including the benchmark, and
pip check passed. PR #20 / Batch A3 was merged at main SHA
`552be0012300ce0d40714b739bbb9e27248c8bca`, the synchronized A4 baseline.

## Product Hardening Batch A3 — Global HTTP request-body boundary

Reconciled Phase 0 PH-004 as permanent FCR-047. FCR-025 covers privacy and
local-state consistency, while FCR-029 covers existing error and recovery
states; neither defines a framework-level body limit before Flask parses form
or multipart input.

The local Flask app now uses a configurable 3 MiB `MAX_CONTENT_LENGTH` request
ceiling. This is deliberately 1 MiB (50 percent) above the existing 2 MiB CSV
payload limit so multipart headers and form encoding have clear capacity. The
two limits remain independent, and configuration rejects a request ceiling
that is not greater than the CSV payload limit.

A lightweight `before_request` check rejects declared oversized bodies before
any route or temporary-state operation, including POST routes that otherwise do
not parse their bodies. Flask's request-reading limit provides the same boundary
during form/multipart parsing. One minimal 413 handler returns only fixed copy
and the configured byte limit; it never reads or echoes submitted content.
Existing `Cache-Control: no-store` and `Pragma: no-cache` response handling
continues to cover 413 responses.

Targeted regressions passed 12/12: seven boundary cases across Direct, Batch
multipart, an unparsed Batch action, Review, Insights notes, and Triage
decisions, plus five unchanged normal-flow checks. They prove no input echo, no
traceback/path disclosure, no state creation or mutation, and the independence
of the CSV byte limit. The full suite passed 148 with 2 opt-in real
model tests skipped; Ruff, strict MyPy for 69 files, compileall, and pip check
passed. Behavioral candidate:
`def0577feb3c43d4e9e81577003c43da821b6ba2`.
The user-approved code review and PR #20 pre-closure final-head CI passed, so
FCR-047 is closed as `VERIFIED` on that exact behavioral candidate. This
governance closure changes no product behavior or test.

Batch A2 was merged through PR #19 at main SHA
`1c9764ba7bcd45b07a07a93077b86070e358a0ab`; this is the synchronized A3
baseline. Feature Freeze remains PASS. PH-005 and PH-007 are not started.

## Product Hardening Batch A2 — Input truthfulness / no silent truncation

Reconciled Phase 0 PH-003 as permanent FCR-046. Existing FCR-003, FCR-006,
and FCR-008 cover input recovery, model-limit communication, and Batch partial
failure separately; none supplied the required cross-provider complete-input
success invariant.

Both pinned Transformers runtimes now encode with special tokens enabled and
`truncation=False`, then compare the real encoded sequence length with an
audited 512-token provider budget before inference. SamLowe declares 512 in its
tokenizer metadata. The pinned Cardiff tokenizer exposes the Hugging Face
unknown-limit sentinel, so the reviewed 512-token contract is explicit and
checked against the loaded model's position capacity. Incompatible finite
metadata fails closed.

Combined analysis preflights both required providers before either inference.
Direct and CLI requests return `model_input_too_long` with an explicit statement
that no truncation or partial analysis occurred. Batch isolates the failure to
the affected row, continues valid rows, and exports no model labels, scores,
identities, or revisions for the failed row. The 20,000-character application
safety ceiling remains separate. No chunking, aggregation, summarization,
model/revision/threshold change, persistence, or successful-result truncation
field was added.

Targeted complete-input regressions passed 9/9. The full suite passed 141 with
2 opt-in integration tests skipped; Ruff, strict MyPy for 69 files, compileall,
and pip check passed. A separate cached, offline run of both real-model smoke
tests passed 2/2. The user-approved code review and PR #19 final-head CI passed,
so FCR-046 is closed as `VERIFIED` on the exact behavioral candidate below.
The exact behavioral candidate is
`31b5e6cf7fc6d551bb72680900976595008d9d7c`; the following documentation
commit does not change that tested behavior.

Batch A1 was merged through PR #18 at main SHA
`1b36fe8c024823c1f4829621a7bcc733b2915c93`; this is the synchronized A2
baseline. FCR-045 remains `VERIFIED`.

## Product Hardening Batch A1 — Ephemeral Batch state integrity

Reconciled Phase 0 findings PH-001 and PH-002 as one permanent product finding,
FCR-045. FCR-036 remains the separate, already-verified confirmation contract
for user-initiated clear; FCR-045 addresses the shared Batch-store root cause:
capacity eviction and missing active-analysis write-back protection.

Batch capacity now blocks new uploads with an explicit conflict instead of
deleting existing work. Synchronous analysis acquires an exclusive in-memory
lease, remains protected from normal TTL purge and clear while active, and may
commit only through its current lease. A rejected write-back is an explicit
409 and never follows the success path. Explicit clear still releases capacity,
inactive TTL expiry remains unchanged, and no database, persistence, recovery
worker, background task, model, threshold, or privacy contract was added.

Targeted regressions cover `capacity+1`, inactive expiry, active analysis across
TTL, duplicate/stale write-back, clear conflict and recovery, and preservation
of existing Batch results, Review, Insights, and linked Triage workspaces when
a new upload is blocked.

PR #18 review found one narrow error-render regression: `/batch/upload` without
a file did not pass the configured concurrent workspace limit to `batch.html`.
Correction SHA `729318c6c253ea8eee8351e766bbcfe7a335c297` restores that context
and adds a configured-limit route regression. Targeted Batch routes passed 6/6,
the full suite passed 132 with 2 opt-in real-model tests skipped, all local
quality checks passed, and PR #18 remote CI passed on Python 3.11/3.12/3.13.
FCR-045 is therefore closed as `VERIFIED`; PH-003 remains outside this batch.

## Feature Freeze closure

Recorded the user's explicit Feature Freeze PASS for tested behavioral SHA
`16acb0f5931b022b57f0c5cdbe4501973aa3ad11` after the candidate-specific
final-head smoke test passed. FCR-044 is manually verified, FCR-002 navigation
verification is re-closed, and V-01 is satisfied by the exact SHA. FCR-042 and
FCR-043 remain non-blocking Product Hardening backlog.

This closure changes governance documentation only. It does not modify product
behavior, models, revisions, thresholds, privacy contracts, workflows, or the
tested behavioral candidate. Release readiness remains No; the next lifecycle
phase is Product Hardening.

## Review ergonomics — Windows one-click launcher

Added `start_social_text_intelligence.bat` at the repository root after explicit
user approval. The launcher resolves the project `.venv` with relative paths,
starts the existing loopback-only web app in offline mode, opens the browser,
and provides setup and shutdown guidance. It installs and downloads nothing and
does not change application, model, privacy, or persistence behavior.

## Feature Complete Review — FCR-044 return navigation

Reclassified FCR-044 as a pre-freeze blocker after candidate-specific manual
review showed that four internal Support Triage views lacked a discoverable
return to the main application and caused material operating difficulty. Added
an explicit `Social Text Intelligence home` link to every non-root workflow
view, including deep Triage and Moderation pages, while preserving each
workflow's own subnavigation and all temporary state.

Reopened FCR-002 navigation verification and added route regressions covering
the four Triage internal views plus Moderation session/review pages. No workflow,
model, data, privacy, persistence, or decision semantics changed.

## Feature Complete Review — pre-freeze blocker corrections

Classified the completed manual review into product findings, QA governance,
and release ergonomics. Recorded FCR-034 through FCR-044 without treating every
questionnaire suggestion as a product FCR. Established a tracked `manual-qa/`
home for the bilingual questionnaire, synthetic samples, and guidance, while
repository ignore rules keep raw results, screenshots, exports, and machine
paths out of Git.

Clarified emotion neutral threshold-fallback copy, added Batch filter anchoring
and destructive-clear confirmation, surfaced Human Review completion and
Context Note UTC timestamps, exposed reliable/unassigned Insight failure
counts, made Triage no-mock state explicit, and restored the linked
Batch-to-Triage entry. These changes preserve models, thresholds, labels,
privacy defaults, denominators, and process-memory boundaries. Feature Freeze
remains pending explicit approval after candidate-specific manual retest.

## Feature Complete Review — local model-cache hardening

Hardened the pinned Cardiff sentiment runtime so Transformers must load the
audited `pytorch_model.bin` artifact and cannot silently create a separate
Safetensors conversion-revision snapshot. Added a regression test for the
immutable revision, offline option, remote-code boundary, restricted weight
loading, and explicit artifact choice.

Repaired the machine-local Hugging Face cache after Windows Developer Mode was
enabled: the duplicate GoEmotions snapshot weight is now a symbolic link to its
content-addressed blob, and the unused Cardiff auto-conversion revision was
removed after real offline inference passed for both providers. Cache repair is
local-only and does not change a model, approved revision, label, score, product
contract, or tracked model artifact.

## Lifecycle alignment after Milestone 10

Created `ROADMAP.md` as the canonical mutable roadmap and
`PROJECT_STATUS.md` as the canonical current-state record. Added the bilingual
Feature Complete Manual Audit and the living manual-QA artifact, then aligned
the README, Charter, and development guidance around the post-M10 lifecycle.

The current phase is Feature Complete Review. Feature Freeze, Product
Hardening, full regression and manual acceptance, and Release Candidate
approval have not started or passed. Former M11–M12 remain deferred
next-version candidates; former M13 is lifecycle evaluation, hardening,
acceptance, portfolio, and delivery work rather than another future feature.

## Milestone 10 — Local Support Triage workbench

Added a separate three-area Support Triage workflow over a versioned,
project-authored synthetic routing guide and 22 stable synthetic tickets.
Successfully parsed batch records are eligible through explicit snapshots even
when NLP inference failed; optional sentiment, emotion, human review, context
notes, and trusted metadata remain supporting context and never determine
routing automatically.

Added typed intents, categories, urgency, recommended queues, escalation
reasons, recommended actions, draft/finalized states, guide provenance,
deterministic mock provenance, structural validation, and non-blocking warning
contracts. Drafts may be incomplete but legal. Finalization is atomic and
freezes an immutable first decision; explicit revisions update a separate
current final decision.

Added Independent and deterministic mock-assisted simulation modes without a
real classifier or LLM. Human forms are never prefilled. First/final field-level
agreement and overrides remain descriptive and are never labeled accuracy,
quality, causal impact, or operator performance.

Added sample-aware summaries, overlapping follow-up reasons, filters, sorting,
and auditable formula-safe CSV export. Workspace-derived source text, NLP
signals, human review, context notes, and trusted metadata are blank by default
and require separate explicit opt-ins. Triage workspaces are process-memory
only, expire after inactivity, and block limits without silent eviction.

Planned feature milestones are now complete, but the project is not
feature-frozen or release-ready. Former Milestones 11–12 are deferred
next-version candidates. Former Milestone 13 is lifecycle work covering
evaluation, hardening, acceptance, portfolio, and delivery.

## Milestone 9 — Moderation training workflow

Added a versioned, project-authored synthetic moderation policy and a 20-case
synthetic training library with stable IDs, policy-clause provenance, complete
reference decisions, acceptable alternatives, sensitive-content markers, and
an explicitly labeled fixture mock provider. The mock provider executes no
model and is never presented as expert judgment or accuracy ground truth.

Added typed moderation contracts and separate structural validation versus
non-blocking policy guidance. Structural errors reject incomplete or conflicting
decisions. Guidance warnings preserve unusual but contextually possible
combinations without rewriting or blocking the user's judgment, and remain in
feedback, comparisons, and export. References distinguish `built_in` from
`self_authored`; the reserved `user_authored` provenance is not exposed as a
current single-user authoring choice.

Added explicit successful-record snapshot preparation, frozen policy/reference
sessions, independent and synthetic-mock-assisted modes, immediate or
end-of-session feedback, immutable first decisions, explicit final revisions,
cancel/restart history, field-level comparison, educational flags, sample-aware
raw summaries, and auditable formula-safe CSV export with privacy-default
exclusions.

Added a three-area Prepare, Train, and Review interface plus configurable
process-memory limits of 100 prepared cases, 50 cases per session, and 20
retained attempts. Limits block new objects without silently deleting existing
work. This milestone adds no live moderation model, automatic enforcement,
support triage, LLM, persistence, platform connector, account, French support,
or new dependency.

## Milestone 8 — Insights and community context

Added reusable trusted-group validation, separate AI/human/agreement
perspectives, exact metric-specific denominators, review-coverage measures, and
per-group sample-size policy. AI activation remains threshold-based and
multi-label; definitive human and disagreement metrics exclude partial and
uncertain dimensions without silently changing the denominator.

Added Group Explorer, two-to-four-group Distribution Comparison, AI vs Human,
Representative Cases, Phrase and Context Notes, and explicit Insight Export to
the existing local Flask workspace. Examples are selected by declared
deterministic rules. Context notes are user-authored, validated, and stored
separately from immutable AI results and human reviews.

Insight summaries retain model and review provenance, disclosures, filters, raw
counts, denominators, and sample warnings. Optional record-level and native-score
export remains off by default, and formula-like user-controlled cells are
escaped. A narrow conformance patch made exports self-auditing with UTC export
and context-note timestamps, metric definitions, configured sample thresholds,
complete input/analysis/review counts, and explicit successful, failed, and
unassigned failed-row group context. Failed rows are grouped only from reliably
validated supported metadata and never by inference. This milestone adds no
model, dependency, LLM narrative, inferred identity, ranking, causality,
automation, persistence, account, cloud service, platform connector, French
support, or moderation workflow.

## Milestone 7 — Human-in-the-loop review

Added a focused review queue for successful batch outcomes. Sentiment and
multi-label emotion use separate accept, correct, and uncertain judgments;
partial work remains unreviewed until both dimensions are decided. Corrected
emotion labels enforce compact-taxonomy membership, uniqueness, dominant versus
secondary separation, stable ordering, and neutral exclusivity. Human fields are
replaced immutably without rewriting the original AI report or provenance.

Added review-state and AI-label filters, safe queue navigation, per-record Accept
Both, optional notes, honest model-human agreement summaries, sentiment confusion,
emotion set comparisons, and bounded confidence-band descriptions. Agreement
denominators exclude whole-record partial reviews, failures, and the uncertain
dimension. No result is described as model accuracy or calibrated confidence.

Added explicit reviewed CSV export with separate human fields, agreement values,
UTC timestamps, failures, AI results, model revisions, and optional native scores.
Spreadsheet formula protection covers review notes and existing user-controlled
cells. Reviews share the bounded, expiring in-memory batch workspace and add no
database, autosave, re-import, training, accounts, cloud service, or Milestone 8
analytics.

## Milestone 6 — Batch input and export

Added an explicit CSV upload, column-selection, preview, and validation workflow.
Supported normalized metadata is trusted only by name; unknown columns are
reported and ignored. Missing IDs receive deterministic row identities, while
duplicate supplied IDs and invalid rows remain visible typed outcomes.

Added resilient sequential batch analysis using the same lazily reused providers,
one outcome per input row, filters, semantically distinct aggregate views, and
explicit normalized CSV export with optional native emotion scores. CSV cells
that could trigger spreadsheet formulas are safely escaped.

Uploads and results use a bounded, expiring in-memory workspace and no durable
storage. This milestone adds no database, automatic export, history, accounts,
French model support, platform connector, or hosted deployment.

## Milestone 5 — Local analysis interface

Added an original local Flask interface for direct English text analysis. The
page displays normalized sentiment and emotion results, optional native scores,
threshold and provenance details, operating mode, first-load guidance, and
plain-language limitations.

Added a thread-safe lazy analysis-service container so both model providers are
constructed once and reused across requests. Expected validation, language,
cache, dependency, and provider failures become safe user-facing messages. The
server binds to loopback and does not log or persist submitted text.

This milestone adds no batch input, history, persistence, accounts, French,
platform connectors, hosted deployment, or separate frontend application.

## Milestone 4 — Licensed fine-grained emotion analysis

Audited English social-text emotion models for license clarity, provenance,
base model, immutable revision, native labels, multi-label support, neutral
semantics, loading format, and technical fit. Approved the MIT-licensed Sam Lowe
GoEmotions model and its Safetensors artifact; documented rejected candidates.

Added local multi-label inference, preservation of all 28 native probabilities,
conservative compact taxonomy mapping, explicit inclusive threshold semantics,
dominant and ordered secondary emotions, neutral fallback, typed validation, and
a single-text combined sentiment/emotion report. Added deterministic tests and
an opt-in real-model combined smoke test.

This milestone adds no UI, batch input, persistence, French capability, platform
connector, remote inference, real user text, dataset, or model weights.

## Milestone 3 — Licensed local sentiment analysis

Audited locally executable sentiment models for license clarity, provenance,
native-label compatibility, loading safety, language, and technical fit. Approved
the Cardiff NLP Twitter-roBERTa sentiment model at an immutable revision and
documented rejected candidates.

Added lazy local inference, model-specific social-text preprocessing, one-to-one
negative/neutral/positive mapping, normalized native and application scores,
single-text service and CLI workflows, explicit unsupported-language and invalid
output handling, deterministic provider tests, and an opt-in real-model smoke
test. Updated licensing, setup, architecture, limitations, and privacy guidance.

This milestone does not add emotion inference, batch input, persistence, a user
interface, remote inference, telemetry, real user text, or model weights.

## Milestone 2 — Text analysis core contracts

Added the model-independent analysis core:

- normalized, immutable text records with explicit metadata validation;
- compact sentiment and emotion taxonomies from the Project Charter;
- separate normalized and model-native score contracts;
- provider identity, model revision, supported-language, and native-label metadata;
- stable sentiment and emotion provider protocols;
- deterministic mock providers for fast, offline tests;
- provider-neutral analysis orchestration and typed error contracts.

The mock providers do not interpret text and are not real NLP models. Milestone 2
adds no model weights, runtime dependency, persistence, UI, network access, or
user data.

## Milestone 1 — Independent local project foundation

Established the project's independent, privacy-first development baseline:

- adopted the Project Charter as the stable product reference;
- added safe Git exclusions and cross-platform text conventions;
- created a minimal dependency-free Python package and diagnostic command;
- added deterministic unit tests and continuous integration;
- documented architecture, privacy, security, development, and model governance;
- clarified that source-code licensing does not relicense models or datasets.

No NLP model, text analysis contract, user interface, persistence layer, user
data, or platform adapter is included in this milestone.
