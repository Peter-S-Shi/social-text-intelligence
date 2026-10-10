# M9 — Formal Windows UAT and accessibility protocol

## Evidence boundary

This is the M9.0 coverage and recorder design, not an executed UAT session.
M9.1 will build fixtures/companion; M9.3 will observe the real Windows PySide6
application. The [evidence contract](V2_M9_EVIDENCE_CONTRACT.md) governs authority
and privacy, and the [exit gate](V2_M9_EXIT_GATE.md) governs owner decisions.
M8 exploratory PASS contains no item-level M9 results. Source/headless tests,
Qt accessibility metadata and screenshots alone cannot establish interactive
UAT or Narrator/high-contrast acceptance.

Only tracked, project-authored synthetic `SYNTH_UAT` fixtures enter these
workflows. Restricted primary evaluation text, model weights, personal details
and local paths do not enter fixtures, the companion or public evidence. Model
quality belongs to the separate [evaluation protocol](V2_M9_EVALUATION_PROTOCOL.md).
Real model readiness can be observed in an authorized later session without
making synthetic expected labels a representative accuracy claim.

## Stable scenario coverage

The IDs below are reserved. M9.1 expands each into atomic, paginated steps named
`<scenario-id>-S01`, `-S02`, etc., with precondition, action, expected result,
fixture/version and evidence requirement. Keep IDs stable across revisions;
version changed steps and preserve prior session meaning. Expected behavior is
specified here; no PASS/FAIL result is prefilled.

| Scenario ID | Action and expected behavior |
| --- | --- |
| UAT-MODEL-01 | First run/readiness: required models absent blocks analysis; only explicit authorized download proceeds; provenance and readiness truthful |
| UAT-MODEL-02 | Offline import/Verify/recovery: corrupt/incomplete/wrong revision stays blocked; verified recovery, progress/cancel and resumed download use existing contracts, no silent substitution |
| UAT-MODEL-03 | English/unsupported/undetermined language examples: warning is visible, detector evidence distinct from supplied language, labels not reclassified by warning |
| UAT-PROJECT-01 | Select CSV/text column and import invalid/duplicate rows: exact validation reasons, deterministic identities and import counts |
| UAT-PROJECT-02 | Analyze with loading/progress and cancel: focus/actions responsive; cancel leaves no partial committed result; retry follows existing semantics |
| UAT-PROJECT-03 | Reopen persistent project/restart and conservative delete: stored AI/review/notes preserved, confirmation truthful, no forensic-erasure claim |
| UAT-RESULT-01 | Select/filter/rebuild Results and switch projects: visible stable record identity preserved only when eligible; Review action targets that record, otherwise disabled |
| UAT-RESULT-02 | Inspect compact/native scores, fallback, invalid rows and inference failures: scores/thresholds explained, independent emotion activations and failure categories truthful |
| UAT-RESULT-03 | Normal/reviewed exports: original rows and failures included as contracted, selected options honored, normalized/model/review provenance accurate |
| UAT-REVIEW-01 | Accept/correct/uncertain separately per task: valid human labels saved, AI immutable, partial/definitive completion and Agreement denominators accurate |
| UAT-REVIEW-02 | Navigate away/save/discard and competing mutation: unsaved changes and conflicts explicit; no silent data loss or wrong-record save |
| UAT-REVIEW-03 | Filtered queue, next action and progress: counters reflect correct queue/scope and review selection; no completion from partial/uncertain dimension |
| UAT-INSIGHTS-01 | Group/multi-group/filter AI/Human/Agreement: trusted metadata only, raw denominators/sample warnings visible; failed rows separate from metrics |
| UAT-INSIGHTS-02 | Add notes/select representative cases: notes remain separate from AI/judgment, existing selection rules and text/privacy behavior truthful |
| UAT-INSIGHTS-03 | Export insights/review/normal CSV with synthetic formula-leading fields: audit counts/provenance accurate and spreadsheet escaping preserved |
| UAT-FAILURE-01 | Two-process contention: scoped project/model locks give actionable errors, no competing commit/corruption or misleading success |
| UAT-FAILURE-02 | Controlled disk-full/read-only/held-file failures: recoverable actionable error and atomic state; log inaccessible test setup honestly |
| UAT-FAILURE-03 | Oversize/model-capacity error and retry/reopen: no truncation or partial analysis, no missing-row success; preserve crash/teardown observations |
| UAT-A11Y-01 | Keyboard-only end-to-end Setup, Projects, Analyze, Results, Review, Agreement, Insights/notes, export and recovery flows: reachable controls, logical order, no trap |
| UAT-A11Y-02 | UI Automation inspection plus actual Narrator navigation/activation in those flows: names/roles/states, record selection, scores/warnings/progress and dialogs readable |
| UAT-A11Y-03 | Focus after dialogs, validation, loading/cancel, unsaved prompt and navigation: focus visible, returned to a usable relevant control |
| UAT-A11Y-04 | Actual Windows high contrast: controls/text/focus/state discernible and critical interactions usable |
| UAT-A11Y-05 | Actual Windows 100%/150% DPI at supported minimum window width: content accessible by intended reflow/scroll, critical actions reachable |
| UAT-A11Y-06 | Actual Windows text-size increase at minimum width: Review's fixed-pixel queue and all critical controls remain readable/usable; record actual setting |

M9.1 should choose bounded synthetic failure setups and documented environment
preconditions. This protocol does not authorize destructive disk exhaustion or
assume the operator has every setup. Missing required environment is `NOT RUN`,
not N/A or automatic PASS. The fixed-pixel queue observation is a test target,
not a predeclared failure/waiver. DPI and Windows text-size are distinct checks.

## Observed decisions and session evidence

The owner or an explicitly owner-authorized interactive operator must execute
the actual Windows application; record authorization as a non-identifying role
and decision reference. Agent source reasoning is not execution authorization or
evidence. Sessions retain:

- tested full application SHA, protocol/scenario/fixture versions, session date,
  Windows/Python/Qt versions, actual platform, DPI/text-size/window width,
  Narrator/high-contrast settings and non-identifying operator role;
- each stable step ID, observed action/outcome, `PASS` / `FAIL` / `N/A` /
  `NOT RUN`, rationale, note, defect ID and optional evidence pointer;
- actual applicability reason for N/A; inability to execute a required scenario
  remains NOT RUN and blocks unconditional formal UAT PASS;
- reproducible failures, severity/blocking rationale, fix SHA, relevant automated
  check and observed retest result linked without overwriting original evidence.

Evidence references identify actual safe screenshots, recordings or observation
notes; no fabricated screenshot or inferred observation. Capture only useful
application content and synthetic data, excluding personal/machine information.
Keep private operator notes/exported sessions locally until privacy review; the
public report may carry sanitized summaries and permitted evidence.

Apply blocking reasoning and Fix → Retest principles from
[Manual Acceptance Gate](MANUAL_ACCEPTANCE_GATE.md), while keeping its historical
V1 web questionnaire separate. Wrong-record actions, state/data loss/corruption,
privacy breaches, unrecoverable critical flows, materially misleading outcomes,
reproducible crashes and failures of required accessibility paths are blocking.
Cosmetic deviations need classification, not automatic blocker status. Required
unexecuted items prevent unconditional PASS. Accepted non-blocking findings need
explicit rationale/owner disposition and stay visible as observed FAILs.
Retest affected paths after a fix; broaden regression only for its blast radius.

## M9.1 offline companion design

Build a separate local V2 HTML evidence recorder, borrowing mature interaction
patterns from the [V1 questionnaire](../manual-qa/manual_review_questionnaire.html)
without rewriting it or copying historical content/results. The companion is
not an STI product UI, application database migration or proof of UAT execution.

Paginate by scenario family with prior/next navigation, stable step IDs,
instructions, expected/observed outcome, status, N/A reason, note, defect ID and
optional evidence reference. Provide keyboard controls, accessible labels and
basic responsive presentation. No network/CDN, account, analytics or upload.
Initial required steps are NOT RUN. Progress counts valid observed PASS/FAIL and
genuinely justified N/A; show FAIL and NOT RUN totals separately. Invalid decisions
do not count as completed; 100% recorded progress is not global PASS. A required
but unavailable environment cannot be marked N/A to complete progress.

### Proposed versioned session schema (`schema_version: 1`)

| Object/field | Contract |
| --- | --- |
| Session | `schema_version`, non-identifying `session_id`, protocol/scenario-pack/fixture versions, created/updated dates, authorization reference |
| Environment | Full tested SHA, OS/Python/Qt/platform, scale and text-size settings, window width, assistive-technology settings, operator role |
| Step record | Known stable `step_id`, enum status, observed action/outcome, rationale, note, defect ID, optional safe evidence reference |
| Defect/retest | Defect ID, classification/rationale, original step/evidence, fix SHA if any, retest step/date/outcome; history retained |
| Export | Versioned JSON session record plus human-readable Markdown/HTML summary; totals derived from validated steps, never trusted from imports |

M9.1 must define concrete field types/length bounds and migration/rejection policy
before implementation, validate imports before mutation, and test schema
round-trip. Reject unsupported versions, malformed types/statuses, duplicate or
unknown IDs, unsafe notes/references and invalid required metadata. Do not execute
imported HTML/script or silently drop invalid records. Import/replacement behavior
must be explicit and protect unsaved state; restore preserves decisions/history
and recomputes progress. Escape notes in rendered and exported Markdown/HTML;
evidence pointers do not trigger automatic network fetches or uploads.

Maintain state locally with visible export/restore controls and warn that browser
local storage can be cleared; export is necessary for durable evidence. Do not
promise persistence merely because the browser retains one session. Automated
schema/state/round-trip tests and interactive browser smoke verify the recorder,
not the desktop scenarios. M9.1 acceptance may PASS infrastructure without
marking a single M9.3 scenario executed.

## Handoff

M9.1 supplies deterministic fixtures, versioned atomic scenario steps, tested
companion and reproduction instructions. M9.3 supplies actual authorized session
JSON, human-readable summaries, Windows/accessibility evidence and defect/retest
dispositions. M9.4 checks completeness against these reserved families and the
[exit gate](V2_M9_EXIT_GATE.md); no M8 result substitutes for a missing session.
