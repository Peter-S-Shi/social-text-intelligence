# Product Roadmap

`ROADMAP.md` is the canonical source for mutable product and lifecycle
planning. Stable product principles and engineering boundaries remain in the
[Project Charter](PROJECT_CHARTER.md); current execution state is recorded in
[Project Status](PROJECT_STATUS.md).

## Completed feature milestones

Milestones 1–10 form the completed feature boundary for the current `0.10.0`
version:

1. independent local project foundation;
2. normalized text-analysis contracts and provider boundaries;
3. licensed local English sentiment analysis;
4. licensed local English fine-grained emotion analysis;
5. local single-text analysis interface;
6. bounded batch CSV analysis and explicit export;
7. independent human review;
8. descriptive insights and context notes;
9. synthetic policy-based moderation training;
10. human-led support triage.

Completion of these feature milestones alone does not establish a lifecycle
gate. Actual gate decisions and live execution state are recorded in
[Project Status](PROJECT_STATUS.md).

## V2 cycle

**Current phase: M9 — Evidence & Formal Acceptance, M9.0 Evidence Design Gate PASS (owner-approved 2026-10-10); M9.1 UAT Infrastructure complete on `main`; M9.2-A feasibility research delivered; owner decisions PENDING. M8 is complete with owner PASS, M7 retains its CONDITIONAL exit, and M9.2 acquisition/evaluation execution and M9.3/M9.4/M10 have not started.** V2 reopens the project from
the verified, public V1 `0.10.0` baseline. The V1 lifecycle below is historical
and unchanged. The Product Scope Gate (decisions in
[V2 Product Discovery](docs/V2_PRODUCT_DISCOVERY.md)), the Architecture Gate
(decisions in
[V2 Desktop Architecture Exploration](docs/V2_DESKTOP_ARCHITECTURE_EXPLORATION.md)),
and the UI/IA Gate (decisions in [V2 UI/IA Decision](docs/V2_UI_IA_DECISION.md),
2026-10-07) are all PASS. The V2 Application Foundation milestone (M3) and the
V2 Persistent Project Foundation milestone (M4) are complete on `main`. **M5 —
V2 Functional Development is complete: M5.0 (Model Provisioner Function Contract &
Foundation), M5.1 (Model Provisioning UI/UX Design, Human Gate PASS), M5.2
(Native Desktop Shell + Model Provisioning UI), M5.3 (Native Project
Workflow), M5.4 (Native Human Review and Reviewed Export), M5.5 (Native
Insights, Context Notes, and Representative Cases), and M5.6 (Language
Detection and Unsupported-Language Warning) are complete on `main`, and the M5
Functional Exit audit is PASS (recorded in [Project Status](PROJECT_STATUS.md)).
M6 — Full UI Integration / Polish is complete on `main`.**
The UI/IA Gate fixed the project-centred
IA and strict feature boundary, retired Moderation Training and Support Triage
from the V2 product surface (V1 `0.10.0` and history preserve them), and
approved V2-4 only as batch progress plus cancellation with no partial commit.
M3 delivered the framework-free application layer (settings and composition
root, use cases, error mapping, a `ProjectRepository` port with an in-memory
implementation, batch progress and cancellation, and the frozen Flask surface
re-pointed at the shared use cases; seams S1–S4, S6, S7). M4 (durable local
project repository) delivered one SQLite file per project behind that port, an
injectable app-data resolver defaulting to Windows LocalAppData, lossless
round-tripping, schema versioning, and WAL-aware deletion; the M5.3 desktop uses it.
M5.0 fixed the model-provisioning product contract
([Model Provisioning Contract](docs/MODEL_PROVISIONING.md)) and delivered its
UI-neutral foundation: typed readiness, progress, and recovery; explicit,
verified, resumable download of the two pinned models; verified import from an
offline/pre-provisioned folder; and analysis that requires ready models and
never downloads. M5.1 designed the desktop provisioning experience from that
contract; the owner approved the design as the M5.2 implementation baseline (H1)
and decided that a confirmed corruption mid-session blocks analysis for the rest
of the session (H2), the one explicitly approved semantic amendment to the
contract, recorded in this closeout. M5.2 delivered the minimal native PySide6 desktop shell
(`sti-desktop`) with the full provisioning experience, wired to the M5.0
contracts, and implemented H2 as one analysis gate. Qt licensing is tracked
(LGPL-3.0 route, Core/Gui/Widgets only) and the pre-distribution LGPL gate
has not passed. M5.3 gave the desktop a project workflow: CSV import into a
persistent project, batch analysis with row progress and cancellation that
commits nothing partial, and open and delete. M5.4 added human review beside the
immutable AI record, stale-write protection for saved judgments, and the
reviewed export. M5.5 added the native insights, context notes, and
representative cases. M5.6 added the last gate-approved V2 addition, language
detection with an unsupported-language warning (V2-3). The M5 Functional Exit
audit then passed: V2-1 to V2-4 are implemented behind stable application
contracts and reachable in the native desktop. Several V1 batch, score, and
agreement detail views were recorded in Project Status as M6 inputs and are now
presented natively. M8 product hardening is complete with the owner's overall
PASS; outstanding item-level risks remain as recorded in its ledgers. Formal
accessibility acceptance, the representative-domain evaluation, the pre-distribution
LGPL gate, packaging, and release work remain separate later gates. V2 is not
release-ready. The package version stays `0.10.0`.

### M9 — Evidence & Formal Acceptance

The [evidence contract](docs/V2_M9_EVIDENCE_CONTRACT.md) defines three independent
streams: Q5 representative-domain model evaluation, formal native Windows UAT,
and formal Windows accessibility. The [evaluation protocol](docs/V2_M9_EVALUATION_PROTOCOL.md),
[UAT protocol](docs/V2_M9_UAT_PROTOCOL.md) and [exit gate](docs/V2_M9_EXIT_GATE.md)
define their design and handoffs. M9.0 design is established with owner Evidence Design Gate PASS (2026-10-10,
reviewed design HEAD `32d8d37`). The 180/45/60 target sample design and
prespecified metrics/uncertainty method are approved; no named data source,
actual sample, or independent annotator is thereby authorized.
The sequence is M9.0 design freeze, M9.1 synthetic pack/offline recorder, M9.2
approved-source evaluation with execution preregistration, M9.3 observed
Windows UAT/accessibility, then M9.4 owner synthesis. M9.1 delivered the
versioned `SYNTH_UAT` pack and offline recorder; M9.2-A research is delivered; source and human commitments remain PENDING. M9.2 acquisition/evaluation execution and M9.3/M9.4 have not started.
M9.2-A delivers the [source-intake research](docs/V2_M9_2A_SOURCE_INTAKE_REGISTER.md)
and [human annotation feasibility plan](docs/V2_M9_2A_ANNOTATOR_FEASIBILITY.md).
Next, the owner reviews source rights/use and independent human commitments.
Every candidate remains PENDING; merging research is not source or Gate approval.
Acquisition and execution preregistration require separately authorized later work.
M8 exploratory acceptance cannot close formal M9 evidence, and no M9 gate
closes M10 packaging/LGPL/release requirements.

### M7 — Pre-Release Feasibility & Risk Gate (complete, CONDITIONAL exit accepted)

M7 tests whether the Windows-first PySide6 desktop has a viable path to packaging
and distribution. The [evidence record](docs/V2_M7_FEASIBILITY_GATE.md) found no
blocking risk: a PyInstaller onedir build ran both pinned models end to end, and no
binding decision needs reopening. The exit is CONDITIONAL because clean-machine
proof, the LGPL deliverables and some evidence gaps remain. M7 added experiment
tooling only; no installer exists and V2 is not release-ready. The sequence stays:
M8 Product Hardening (with an early owner-led exploratory trial), M9 Evidence and
Formal Acceptance (owner-operated Scenario-Based UAT and a local HTML acceptance
companion), M10 production packaging, final LGPL compliance, installer and release
candidate verification. M8 is complete on `main`: Track A technical hardening
([ledger](docs/V2_M8_TRACK_A_LEDGER.md)) and Track B UI fidelity
([record](docs/V2_M8_TRACK_B_FIDELITY.md)) are merged, and the owner approved
the overall UI fidelity outcome and completed the early exploratory trial with
an overall PASS on 2026-10-10. This is not M9's formal acceptance. Codex has delivered the M9.0 design and the
owner approved the Gate on 2026-10-10. M9.1 infrastructure is complete on `main`;
M9.2 acquisition/evaluation execution, M9.3/M9.4 and M10 have not started. M7's
CONDITIONAL exit is preserved: open risks close only where the Track A ledger
shows affirmative evidence; remaining decisions and unverified conditions stay open.

### M6 — Full UI Integration / Polish (complete)

M6 integrates the previously deferred V1 score breakdowns, per-row validation
and failure reasons, Results filters and export, and Agreement detail over the
existing use cases. It also closes the native layout and focus gaps within the
fixed project-centred IA and the visual separation of the immutable AI record
from human judgment. The [F-ID acceptance record](docs/V2_M6_ACCEPTANCE.md)
and [Windows Qt visual evidence](manual-qa/m6-visual-evidence/README.md) cover
the exact milestone boundary. It adds no new metrics or product concepts.
At the M6 exit, the next required action was to scope the next V2 milestone.
M8 later completed with an owner PASS; M9 formal acceptance, representative-domain
evaluation, LGPL compliance, packaging, and release-candidate or distribution
work remain separately gated. V2 is not release-ready.

## V1 final lifecycle phase (historical)

**V1 final phase: Public Portfolio Delivery**

Feature Complete Review is completed, Feature Freeze is PASS, Product
Hardening is complete, Full Regression and Manual Acceptance is PASS, and
the Release Candidate Gate is PASS. The repository owner's Version /
Delivery Decision approved public portfolio delivery of `0.10.0`; the
GitHub repository is public. No version tag or GitHub Release has been
created, and none is implied by this decision. Findings belong in the
[Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md), while
the detailed live state belongs only in [Project Status](PROJECT_STATUS.md).

## Feature Complete Review

**Status: Completed.** The following purpose and exit criteria remain the
canonical plan and historical gate definition.

### Purpose

- inspect the current product as one coherent user experience;
- identify missing, redundant, misleading, inaccessible, or fragile behavior;
- distinguish current-version blockers from optional future expansion;
- make explicit keep, change, remove, merge, hide, simplify, reject, and defer
  decisions before scope freezes.

### Allowed decisions

- accept existing behavior;
- fix a defect;
- make a must-add-before-freeze proposal;
- remove, merge, hide, or simplify a current capability;
- reject a proposed change with recorded rationale;
- defer a proposal to the next-version backlog.

Every finding must be classified before implementation. New capabilities are
not assumed to belong in the current version merely because they are discovered
during review.

### Required outputs

- all major user workflows manually exercised;
- every product finding classified;
- all must-add-before-freeze items implemented or formally rejected;
- all approved remove, merge, hide, or simplify decisions completed;
- deferred next-version work separated from current-version scope;
- the audit artifact, manual-QA record, and `PROJECT_STATUS.md` updated.

### Exit criteria

Feature Complete Review may end only when every audit item has a recorded
disposition, every accepted current-version change is complete and validated,
no unclassified scope decision remains, and an explicit Feature Freeze Gate
decision is ready.

## Feature Freeze Gate

**Status: PASS.** The explicit decision is recorded in the
[Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md); current
gate state remains in [Project Status](PROJECT_STATUS.md).

Feature Freeze is a formal, recorded decision that the current-version feature
set is closed. It has not passed merely because Milestone 10 or the feature
audit is complete.

After Feature Freeze, work is normally limited to:

- bug fixes;
- privacy or security fixes;
- data-integrity fixes;
- usability corrections;
- accessibility fixes;
- error-state improvements;
- regression tests;
- documentation corrections;
- release preparation.

The following are prohibited without reopening the gate:

- new input domains or languages;
- new model systems;
- platform connectors;
- accounts or authentication;
- persistence;
- new top-level workflows;
- other behavior that materially expands current-version product scope.

A reopening decision must identify the need, scope, risks, owner, affected
artifacts, and required regression. It must update the Feature Complete Manual
Audit and `PROJECT_STATUS.md` before implementation.

## Product Hardening

**Status: Complete.** Ten batches (A1–A10) closed ten permanent findings
(FCR-027, FCR-030, FCR-045–052) covering every approved Phase 0 finding
(PH-001–PH-010) plus one independently discovered applied-state reflection
defect. Each batch's behavioral candidate and reviewed head passed its own
targeted and full regression, formal review, and remote CI; the closure
baseline `fc230c587c245cdb1cd75b399c91eb38ac82d768` also passed independent
post-merge `main` CI. FCR-042 and FCR-043 remain explicitly accepted `OPEN`
non-blocking backlog — evaluated and found to carry no correctness, safety,
privacy, accessibility, or state-integrity risk, so their absence does not
block this closure. Detailed disposition is recorded in the
[Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md).

Product Hardening was quality convergence over the frozen feature set. It
included:

- defect discovery and repair;
- UX and terminology consistency;
- keyboard and accessibility correction;
- error, empty, expiry, and recovery states;
- privacy-default and formula-safety regression;
- performance and bounded-capacity checks;
- documentation-to-behavior consistency;
- removal of dead, duplicated, or misleading paths.

Hardening must not conceal new feature development. Any change that expands the
frozen feature set requires an explicit freeze-reopening decision.

## Full Regression and Manual Acceptance

**Status: PASS — 2026-08-14.** A repository-owner-authorized agent-operated
session executed a repository-owner-defined minimum required fresh-interaction
profile of 20 questionnaire items against tested SHA
`71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1`, using a real offline local server
and a real browser. All 20 items PASS; 0 FAIL; 0 blocking defects under the
[Manual Acceptance Gate Standard](docs/MANUAL_ACCEPTANCE_GATE.md). Automated
Full Regression evidence reused the independent post-merge `main` CI already
recorded for that SHA (pytest, Ruff, MyPy, compile, dependency install) plus
existing Product Hardening real-model/concurrency/HTTP-boundary/browser-security
evidence, per that SHA's Product Hardening record. FCR-042 and FCR-043 dispositions
are untouched. All nine carried-forward pre-freeze "OPEN verification" items
(FCR-003, 005, 014, 015, 017, 021, 023, 026, 031) received explicit
disposition and closed `VERIFIED` before this phase's PASS, using existing
Feature Freeze, Product Hardening, and regression-test evidence plus this
session's own fresh evidence where directly applicable (FCR-003, FCR-026);
no carried-forward verification item remains open. Full detail is recorded in
the [Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md).

This phase required:

- the complete automated test and quality suite;
- browser-based and manual QA across representative workflows;
- project-authored synthetic datasets, including partial failures and sample
  threshold boundaries;
- privacy-default, explicit opt-in, `no-store`, and formula-injection checks;
- current audit, QA, status, and defect records;
- closure or formal disposition of every blocking defect, including the
  pre-freeze "OPEN verification" checklist items carried forward from
  Feature Complete Review (FCR-003, 005, 014, 015, 017, 021, 023, 026, 031)
  — all nine closed `VERIFIED` before this phase's PASS.

The canonical repeatable checklist is
[Manual QA](manual-qa/manual_review_questionnaire.html). A completed exported record is
evidence for a specific tested version; it does not replace the living
checklist. What PASS, FAIL, and N/A mean for this phase, who may execute it,
and what evidence a decision requires are defined once, permanently, in the
[Manual Acceptance Gate Standard](docs/MANUAL_ACCEPTANCE_GATE.md).

## Release Candidate and Packaging

**Status: PASS — 2026-08-14.** RC candidate SHA
`427984a5d39b7e20eafc53e588aa5a53b6bd320d` (differs from the Manual
Acceptance tested SHA only by governance/docs/lifecycle-test changes, so
Manual Acceptance runtime evidence remains valid and was not retested).

An RC decision freezes the candidate contents and verifies:

- version and package metadata: `social-text-intelligence` `0.10.0`,
  `Requires-Python >=3.11`, console scripts `sti`/`sti-web`, extras
  `sentiment`/`emotion`/`web`/`dev` — confirmed consistent in
  `pyproject.toml` and the built wheel's `METADATA`;
- clean installation and reproducible local startup: a wheel built from a
  clean detached checkout installed cleanly with no extras (`pip check`
  clean, `sti about`/`sti contracts` work) and with the `web` extra
  (`sti-web --help` works, server binds to `127.0.0.1` only, the installed
  wheel's home page and static assets load, proving templates/static were
  actually packaged);
- supported Python environments: exact-SHA CI green on 3.11/3.12/3.13,
  reused rather than re-created locally; local wheel smoke on the available
  Python 3.12;
- model revision and optional dependency behavior: pinned sentiment/emotion
  model revisions match the approved records exactly and are passed as
  explicit non-floating arguments; no weights bundled in the wheel; with no
  model extras installed, a Direct analysis submission fails intentionally
  and comprehensibly (a clear in-page error, HTTP 200, no traceback) rather
  than crashing or silently misbehaving;
- licenses, attribution, and notices: `LICENSE`, `THIRD_PARTY_NOTICES.md`,
  `pyproject.toml`, and the wheel's `METADATA` are mutually consistent;
- final privacy and repository-hygiene review: no weights, databases,
  credentials, or secrets in tracked files or the built wheel; expected
  ignore boundaries (`dist/`, `build/`, `model_cache/`,
  `manual-qa/results/`) remain in place;
- full automated and manual regression: exact-SHA CI plus the reused
  2026-08-14 Full Regression and Manual Acceptance PASS;
- documented release blockers and their disposition: **none found**.

An RC label does not automatically imply `1.0.0`, production readiness, public
hosting, or public release. Version and delivery decisions require their own
explicit gate; at this historical RC stage, the next required action was the
repository owner's Version / Delivery Decision. FCR-042 and FCR-043 remain `OPEN`
non-blocking backlog, unchanged by this gate.

## Public Portfolio Delivery

**Status: PASS — 2026-08-15.** The repository owner made the previously
pending Version / Delivery Decision: current version `0.10.0` is approved
for public portfolio delivery. The GitHub repository visibility is public.

This decision covers public portfolio delivery specifically. No version tag
or GitHub Release has been created for `0.10.0`, and none is implied by it;
a formal tagged release remains a separate, independent decision for the
repository owner to make later if ever desired. FCR-042 and FCR-043 remain
`OPEN` non-blocking backlog, unchanged by this closure.

## V2 disposition of former V1-deferred items

These items were deferred out of V1 `0.10.0` hardening and stayed outside the
V1 feature boundary. The V2 Product Scope Gate (PASS, 2026-10-06) dispositioned
them; the authoritative record is section 11 of the
[V2 Product Discovery](docs/V2_PRODUCT_DISCOVERY.md) record.

| Former V1-deferred item | V2 disposition |
| --- | --- |
| Local persistence | **Promoted to committed V2 scope** as persistent local projects; storage direction decided at the Architecture Gate (one SQLite file per project, kept until manually deleted); implemented at the repository layer by M4 — V2 Persistent Project Foundation and exposed in the desktop by M5.3 (both complete on `main`) |
| French or multilingual capability | **Conditional** on a future licence-and-evaluation spike; V2 itself requires only language detection and an unsupported-language warning |
| Transcript and long-form analysis | **Evidence-gated**, not committed |
| Local theme discovery and optional local LLM provider (raised in V2 discovery) | **Evidence-gated**, not committed |
| Platform connectors | **Rejected for V2** |
| Accounts, shared workspaces, or cloud services | **Rejected for V2** |
| Other additional models, input domains, and top-level workflows | Not committed; considered only through the V2 gates |

The V1 `0.10.0` boundary is unchanged: persistence and the other items above
are not part of the shipped V1 runtime, and none of this work may be mixed into
V1 defect or hardening work.
