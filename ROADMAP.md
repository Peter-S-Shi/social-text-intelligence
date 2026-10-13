# Product Roadmap

`ROADMAP.md` is the canonical source for mutable product and lifecycle
planning. Stable product principles and engineering boundaries remain in the
[Project Charter](PROJECT_CHARTER.md); current execution state is recorded in
[Project Status](PROJECT_STATUS.md).

## Current execution phase — Portfolio Packaging (2026-10-13)

<!-- STI_PP4_CURRENT_STATE_2026_10_13 -->
**Current disposition: V2 development COMPLETE; v2.0.0 CONDITIONAL PORTFOLIO RELEASE PUBLISHED; PP delivery COMPLETE upon merging this documentation bundle.** The Windows x64 [installer release](https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/v2.0.0) is public, immutable and tied to the frozen application tag at `819e048c399799ed78da83c5711ed3b40d5c4caf`. The public-phase verification reported all 17 release-gate checks passing, with B1's *operational source-access prerequisite* closed for that release; this is neither an independent legal certification nor an assertion that the frozen internal `distribution_permitted=false` flag changed.

PP-1 audited existing Qt screenshots; PP-2 reorganized the recruiter-facing [README](README.md) around the installer and product; PP-3 authored an original conceptual hero and an [engineering case study](docs/PORTFOLIO_CASE_STUDY.md); PP-4 integrates these artifacts with current-status corrections. Existing M8 screenshots use synthetic records and stand-in model providers: they demonstrate real native UI, **not real-world model accuracy**. No installer rebuild, rescreenshot, or product-code change is part of PP.

Residuals remain explicit: unsigned installer/SmartScreen risk and two S5 icon-evidence gaps were Owner-accepted; the final installer smoke test is Owner-reported PASS; full M9.2 real-domain evaluation, M9.3 formal UAT/accessibility, M9.4 synthesis and the remaining formal C16 evidence are not claimed complete. After this boundary the next activity is optional local-workspace cleanup, not further V2 product development by default. For authoritative live status see [Project Status](PROJECT_STATUS.md). The subsequent V2/M10 sections are **chronological milestone records**; statements written in those sections about what was not yet published apply to the historical milestone date, not to the current product release.

## Completed feature milestones

Milestones 1–10 form the completed feature boundary of the V1 `0.10.0`
baseline (the application version is now `2.0.0`; see Release-5A-1):

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

> The V2 cycle below is a historical engineering account. Live status is above.

## V2 cycle

**Historical milestone snapshot (pre-Release-5B/5C): M10 engineering priority — M10-A packaging foundation and M10-B compliance engineering established on `main`; M10-C installer engineering established on `main`; M10-D release readiness dossier established; M10-E1 distribution unblocking established (B2 resolved by removal; B1, B4 and B6 narrowed but OPEN; B3 and B5 need owner decisions); M10-E2 blocker closure engineering established (B3 CLOSED by an official CPython runtime and no Microsoft runtime redistribution; B1 and B4 narrowed but OPEN; B5 and B6 OPEN pending owner/legal decisions and the owner toolchain); Core + Optional Components strategy, R1 and plan revision 2 approved; M10 S1 optional language model COMPLETE on `main` (engineering validation passed on a real frozen build and internal installer; S5 clean-machine matrix NOT RUN; real in-app downloads were later owner-witnessed under S5-NET-001 (PR #69); the py3langid model is not in the core installer and is downloaded from upstream only on user request; language detection restored once installed; B5 not derived for the installer contents, corpus terms unverified; R2 parked in draft PR #62); M10 S2 B4 licence materials COMPLETE on `main` (PR #65; Rust crate texts complete; B4 OPEN, narrowed to Intel OpenMP redistribution authorization, which is not approved); M10 S3 COMPLETE on `main` (PR #66; E4 modified-source QtCore-only replacement PASS, so B6 CLOSED on the narrower M10-E2 criterion; the M10-E1 Gui/Widgets/plugin rebuild was not exercised); M10 S4 B1 decision memo on `main` (PR #67); M10 S4 phase 2 on `main` (PR #68: the owner's D1–D3 engineering direction is recorded and validated in the packet, and installer blockers are derived from the packet; legal confirmation pending, producer correspondence unproven, D4 unresolved with B4; B1 OPEN); M10 S5-NET-001 download certificate fix on `main` (PR #69: model downloads verify with the OS trust store through a local truststore context; owner VM re-verification of S5-NET-001 PASS at product level; S5 matrix not run at that point); M10 S5-A harness hardening on `main` (PR #70: the clean-machine harness takes blockers from the validated receipt, has explicit missing/present VC++ runtime modes, and never states clean-machine acceptance; since run in S5); M10 S5-UI-001 application icon on `main` (PR #71: the owner-approved icon is embedded in both executables and used by the window, Start Menu and uninstall entry; the owner's Windows check is pending); M10 S5 clean-machine stages A and B run by the owner on an isolated VM, with the harness junction-cleanup fix on `main` (PR #72); raw guest evidence reviewed (PR #73: H2-A, C02–C12 and C14 PASS on the reviewed automated evidence, C07 owner-witnessed under its limited definition, icons 2 of 4 confirmed and 2 of 4 NOT DETERMINED as accepted carried-forward gaps, Release-1 gate OWNER-APPROVED CONDITIONAL EXIT, not a release permission); Release-2 compliance closure engineering on `main` (PR #74: Intel OpenMP shipped from Intel's author-signed NuGet package under the Intel Simplified Software License, D4 boundary scoped in the notices, B1 source-access page drafted; B1 and B4 legally OPEN pending decisions LD1–LD6); Release-2 final licence decisions on `main` (PR #75: LD1–LD6 owner-assessed with disclosed residual risks, not an external legal certification; the oneTBB notice NOT REQUIRED; B4 closed in the packet derivation; B1 OPEN until the installer-page source link is verified (see the Release-3/4A entry); `distribution_permitted` false pending the installer-page source link and a separate Owner Release Gate); Release-3 public source access (source-only GitHub release `sources-qt-6.11.2`, immutable, 13 verified assets, source-access materials only) and Release-4A integration on `main` (PR #76: the permanent release URL is pinned in `SOURCE_HOSTING.json` and named in the packaged notices; the packet checks tell valid hosting from missing, inconsistent or substituted evidence; the Intel `NOTICE.md` is pinned by content; B1 stays OPEN, narrowed to the installer download page linking to the release with that same-page link verified, and no such page is live; `distribution_permitted` false; Release-4B private release candidate and two-phase publication gate on `main` (PR #77: `release_gate.py` checks the unpublished draft before Owner approval and the public page after publication, and only the public phase can report B1 operational closure; the packaged text no longer asserts whether an installer page exists; a candidate installer profile with a release notice and its own gates; a private candidate built and checked, not published; the application version is later set to `2.0.0` by Release-5A-1 and the planned tag `v2.0.0` is not created; no release made; B1 OPEN until a passing public-phase check; `distribution_permitted` false); Release-5A-1 version freeze on `main` (PR #78: the Owner-approved application version `2.0.0` in `pyproject.toml` and `__version__`, installer names derived from it, `STI-2.0.0-x64-setup.exe` for the candidate profile; V1 `0.10.0` and Release-4B records kept as history; a private preliminary candidate was built and checked and is not the release installer; a fresh build from the merged `main` commit is required; no tag `v2.0.0`, Draft or public Release exists; B1 OPEN; `distribution_permitted` false)); distribution gate BLOCKED; M9.0 remains historical approved design, M9.1 is COMPLETE and merged, and M9.2–M9.4 are deferred by owner. M8 owner PASS and M7 CONDITIONAL risks are preserved; later distribution gates remain open.** V2 reopens the project from
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
release-ready. The package version stayed `0.10.0` through V2 development until Release-5A-1 set `2.0.0`.

### M9 — Evidence & Formal Acceptance

The [evidence contract](docs/V2_M9_EVIDENCE_CONTRACT.md) defines three independent
streams: Q5 representative-domain model evaluation, formal native Windows UAT,
and formal Windows accessibility. The [evaluation protocol](docs/V2_M9_EVALUATION_PROTOCOL.md),
[UAT protocol](docs/V2_M9_UAT_PROTOCOL.md) and [exit gate](docs/V2_M9_EXIT_GATE.md)
define their design and handoffs. M9.0 design is established with owner Evidence Design Gate PASS (2026-10-10,
reviewed design HEAD `32d8d37`). The 180/45/60 target sample design and
prespecified metrics/uncertainty method are approved; no named data source,
actual sample, or independent annotator is thereby authorized.
The historical approved evidence sequence is M9.0 design freeze, M9.1 synthetic pack/offline recorder, M9.2
approved-source evaluation with execution preregistration, M9.3 observed
Windows UAT/accessibility, then M9.4 owner synthesis. M9.1 delivered the
versioned `SYNTH_UAT` pack and offline recorder; M9.2–M9.4 are deferred by owner while M10 engineering takes priority.
M8 exploratory acceptance cannot close formal M9 evidence, and no M9 gate
closes M10 packaging/LGPL/release requirements.

### Owner reprioritization — M10-A packaging foundation

The owner explicitly prioritizes M10 engineering and defers M9.2–M9.4.
This preserves the approved M9.0 design and completed M9.1 infrastructure;
deferral does not waive Q5 real-domain evidence for model capability claims.
M10-A establishes the proven M7 Windows PyInstaller onedir route as a repeatable
[packaging foundation](docs/V2_M10_A_PACKAGING_FOUNDATION.md), with offline
startup/dependency checks and temporary-data smoke, keeping weights external.
M10-C installer engineering is established; next execute isolated clean-machine validation and close B1 and B4–B6 (see M10-E2) before distribution clearance.
The optional 30-minute owner packaged-app smoke is planned **NOT RUN**.
Clean-machine proof, LGPL/compliance, signing and release gates remain open;
formal Windows UAT/accessibility and M9.4 owner synthesis are not completed.

### M7 — Pre-Release Feasibility & Risk Gate (complete, CONDITIONAL exit accepted)

M7 tests whether the Windows-first PySide6 desktop has a viable path to packaging
and distribution. The [evidence record](docs/V2_M7_FEASIBILITY_GATE.md) found no
blocking risk: a PyInstaller onedir build ran both pinned models end to end, and no
binding decision needs reopening. The exit is CONDITIONAL because clean-machine
proof, the LGPL deliverables and some evidence gaps remain. M7 added experiment
tooling only and did not deliver an installer; M10-C now supplies internal installer engineering, while V2 is not release-ready. The sequence stays:
M8 Product Hardening (with an early owner-led exploratory trial), M9 Evidence and
Formal Acceptance (owner-operated Scenario-Based UAT and a local HTML acceptance
companion), M10 production packaging, final LGPL compliance, installer and release
candidate verification. M8 is complete on `main`: Track A technical hardening
([ledger](docs/V2_M8_TRACK_A_LEDGER.md)) and Track B UI fidelity
([record](docs/V2_M8_TRACK_B_FIDELITY.md)) are merged, and the owner approved
the overall UI fidelity outcome and completed the early exploratory trial with
an overall PASS on 2026-10-10. This is not M9's formal acceptance. Codex has delivered the M9.0 design and the
owner approved the Gate on 2026-10-10. M9.1 infrastructure is complete on `main`;
M9.2–M9.4 are deferred by owner; M10-A packaging foundation is complete, and later M10 distribution gates remain open. M7's
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

### M10-B — Compliance engineering established; distribution BLOCKED

The actual Windows onedir audit, license/source packet, prominent Qt notice and
bounded DLL replacement experiments are established on `main`.
The two Qt-only replacement experiments failed; compatible replacement is
unverified and explicitly blocks distribution (B6).
[The compliance record](docs/V2_M10_B_DISTRIBUTION_COMPLIANCE.md) retains exact
source, software-renderer, runtime redistribution and embedded dependency/model
obligations as blockers. The next required action is to resolve those blockers;
no compliance certification, distribution or release readiness is
claimed. M9.2–M9.4 remain deferred and Q5 is not waived. The owner optional
30-minute packaged-app smoke remains planned NOT RUN.

### M10-C — Installer engineering established; clean-machine NOT RUN

The bounded Inno Setup 6.7.3 per-user workflow is established on `main`,
retaining the M10-A onedir and M10-B license/source packet. Actual current
Windows development-host installation, native launch, runtime/license checks,
reparse refusal, logged-file uninstall, reinstall and synthetic byte preservation
PASS. [The installer record](docs/V2_M10_C_WINDOWS_INSTALLER.md) contains the
repeatable isolated Windows protocol and precise NOT RUN matrix. Clean-machine
acceptance and missing-model/download-cancel UI checks remain NOT RUN. The next
action is to execute that isolated matrix and close the blockers; after M10-E2, B1 and B4–B6 remain BLOCKED.
Owner 30-minute smoke remains planned NOT RUN; no signing, publication, formal
UAT or release readiness is claimed. M9.2–M9.4 remain DEFERRED and Q5 unchanged.

### M10-D — Release readiness dossier and decision gate established; binary distribution BLOCKED

The auditable [release readiness dossier](docs/V2_M10_D_RELEASE_DOSSIER.md)
synthesizes M10-A packaging, M10-B compliance, M10-C installer engineering, and
retained M7/M8/M9 risks across six stratified layers. Three distinct operational
surfaces are defined: public source-code portfolio presentation is SUPPORTED;
non-distributable product demonstrations are SUPPORTED UNDER CONTROLLED CONDITIONS;
downloadable binary distribution is PROHIBITED / BLOCKED due to open legal blockers
B1–B6, unverified clean-machine state, and potential unsigned binary friction;
Q5 representative-domain evidence remains required before model capability claims.
Defensible recommendation is GO for source portfolio presentation and
NO-GO for binary distribution. The formal release decision remains pending the
repository owner. M9.2–M9.4 remain DEFERRED, the optional 30-minute owner smoke
remains NOT RUN, and Q5 is unchanged.
### M10-E1 — Distribution unblocking engineering; distribution still BLOCKED

The [M10-E1 record](docs/V2_M10_E1_DISTRIBUTION_UNBLOCKING.md) verifies the shipped Qt binaries against the official Qt build SBOMs and the tagged source archives. It explains the M10-B replacement failures as Qt's version-tagged private API, and demonstrates same-version and coherent-set replacement. It keeps the binding layer replaceable and stops shipping the unused software renderer.

Blocker status: B2 is resolved by removal; B1, B4 and B6 are narrowed but OPEN; B3 and B5 need owner/legal decisions. Next: those owner decisions, the defined E4 modified-source Qt rebuild, the B4 crate notices and the isolated clean-machine matrix. No binary is published.

### M10-E2 — Blocker closure engineering; B3 closed, distribution still BLOCKED

The [M10-E2 record](docs/V2_M10_E2_BLOCKER_CLOSURE.md) closes B3:

- the build runs under, and ships, the official PSF CPython 3.13.16 runtime,
  checked file by file;
- no Microsoft Visual C++ runtime file is redistributed;
- the per-user installer requires the system runtime and never elevates.

It also:

- verifies all 96 Qt translations and the pyside-setup tag correspondence;
- removes the unused `hf_xet` and `protoc.exe`;
- adds an exact tokenizers `Cargo.lock` receipt;
- prepares the E4 modified-Qt rebuild without installing any toolchain.

Next: owner/legal decisions for B1 and B5, the owner's MSVC toolchain for E4
(B6), the B4 notice texts and the clean-machine matrix. No binary is
published.

### Core + Optional Components plan (strategy and revision 2 approved)

The [plan](docs/V2_M10_CORE_OPTIONAL_PLAN.md) sets the distribution strategy:

- Qt/PySide6 and the rest of the essential stack stay in the installer.
- The VC++ runtime stays an external prerequisite (R1); R2 is parked in draft
  PR #62.
- Language detection stays in the release:
  - The py3langid model is excluded from the core installer.
  - It is provisioned on user request from its upstream `v0.4.0` tag, pinned by
    SHA-256.
  - Until then, the existing "Language check unavailable" state applies.

B1, B4 and B6 finish through narrow tasks (S2–S4), then the clean-machine matrix
(S5). #61, #63 and #64 were merged in that order with the owner's approval; #62 stays parked and unmerged.

**S1 complete on `main`** (PR #64, [record](docs/V2_M10_S1_OPTIONAL_LANGUAGE_MODEL.md)). Engineering validation passed on a real frozen build and an internal installer; the S5 clean-machine matrix is NOT RUN, and the real in-app download was later owner-witnessed under S5-NET-001. **S2 complete on `main`** (PR #65, [record](docs/V2_M10_S2_B4_NOTICES.md)): Rust crate licence texts are complete; B4 stays OPEN because Intel OpenMP redistribution authorization is not approved. **S3 complete on `main`** (PR #66, [record](docs/V2_M10_S3_E4_MODIFIED_QT.md)): QtCore-only E4 PASS, so B6 is CLOSED on the narrower M10-E2 criterion (Gui, Widgets and plugins were not rebuilt from modified source). **S4 decision memo** (PR #67, [memo](docs/V2_M10_S4_B1_DECISION_MEMO.md)): it recommends the upstream-source route as the preferred route for owner/legal acceptance, with exact producer correspondence unproven. **S4 phase 2** (PR #68, [record](docs/V2_M10_S4_PHASE2_B1_DECISION_RECORD.md)) records the owner's D1–D3 engineering direction in the packet. B1 stays OPEN pending legal confirmation and D4. The model is absent from both. Installing the pinned upstream bytes restores detection. **S5-NET-001 fixed on `main`** (PR #69, [record](docs/V2_M10_S5_NET001_TLS_FIX.md)): the clean-VM test found that in-app downloads failed certificate verification, and they now verify with the OS trust store. The owner's VM re-verification passed at product level. The S5 matrix had not run at that point. **S5-A harness hardening on `main`** (PR #70, [record](docs/V2_M10_S5A_HARNESS_HARDENING.md)): H1–H3 are fixed (blockers taken from the receipt, explicit runtime modes, no self-acceptance). The harness has since been run in S5. **S5-UI-001 icon on `main`** (PR #71, [record](docs/V2_M10_S5_UI001_APP_ICON.md)): the owner-approved icon is used by both EXEs, the window, the Start Menu and the uninstall entry. The owner's Windows check is pending. **S5 stages A and B run and evidence reviewed** (PR #72 and #73, [completion record](docs/V2_M10_S5_COMPLETION_RECORD.md)). The owner ran both stages on isolated snapshots and exported the raw evidence. Both hash chains are complete. H2-A, C02–C12 and C14 PASS on the reviewed automated evidence; C01 PASS on the host build; C13 has automated checks only; C15 BLOCKED; C16 NOT RUN; no FAIL item. C07 has the owner-reported human witness under its limited definition. Icons: 2 of 4 formal places confirmed (title bar, taskbar); the Start Menu menu UI and Settings › Apps are NOT DETERMINED for lack of visual evidence, not a defect; the Start Menu programs-folder shortcut matches as supporting evidence. The harness junction cleanup that interrupted the first Stage B attempt is fixed on `main`, byte-identical to the harness Stage B ran. **Release-1 gate: OWNER-APPROVED CONDITIONAL EXIT**, with the two icon gaps carried forward. It is not a release or distribution permission.

**Release-2 compliance closure engineering on `main`** (PR #74, [record](docs/V2_R2_COMPLIANCE_CLOSURE.md)). The Intel OpenMP DLLs now ship from Intel's author-signed NuGet package `intelopenmp.redist.win` 2026.1.0.239 under the Intel Simplified Software License, with fail-closed pins; the wheel's Developer Tools EULA is recorded only as superseded. Intel's no-reverse-engineering term is scoped to the two Intel files in the notices (D4 boundary). The B1 source-access page is drafted, not published. B1 and B4 stay legally OPEN pending the bounded decisions LD1–LD6; `distribution_permitted` stays false.

**Release-2 final licence decisions on `main`** (PR #75, [record](docs/V2_R2_LICENSE_DECISIONS.md)). The owner assessed LD1–LD6, including the residual risks, the Intel high-risk-use disclaimer and the oneTBB notice finding (NOT REQUIRED). These are internal compliance decisions, not an external legal certification. `distribution/legal/LICENSE_DECISIONS.json` is validated against an exact reviewed constant. With it, B4 is no longer derived, and B1 is narrowed to its one operational prerequisite: public source access under GPLv3 §6(d), prepared in `distribution/release-source-page.md` but not published. B1 is never removed by a record. Next (updated by Release-4A below): a live installer download page, then a separate Owner Release Gate (C15 signing/SmartScreen BLOCKED, C16 NOT RUN, carried-forward icon gaps). `distribution_permitted` stays false.

**Release-3 and Release-4A on `main`** (PR #76, [record](docs/V2_R4A_PUBLIC_SOURCE_ACCESS.md)). The source-only GitHub release `sources-qt-6.11.2` is public and immutable, pinned to `de247c5`, with 13 verified assets; GitHub displays it as Latest, an accepted presentation deviation. `distribution/legal/SOURCE_HOSTING.json` is validated against an exact reviewed constant and the source manifest, provenance and replacement-guide hashes. A valid record narrows B1 to the installer download page linking to the release with a verified same-page link; no such page is live, and B1 is never removed by a record. The Intel `NOTICE.md` is pinned by content. `distribution_permitted` stays false; C15, C16 and the S5 icon gaps are unchanged.

**Release-4B on `main`** (PR #77, [record](docs/V2_R4B_RELEASE_GATE.md)). An immutable release cannot be edited after publication and its public page exists only afterwards, so the evidence is split: the draft is checked before Owner approval, and the public page after publication. Only the public check reports B1's operational closure; the packet inside the installer stays B1 by design and no longer asserts whether an installer page exists. A candidate installer profile (release notice, own name, extra gates) leaves the internal profile unchanged. A private candidate (`STI-0.10.0-x64-setup.exe`) was built and checked, not published. The application version was later set to `2.0.0` (Release-5A-1 below). Next: authorization for the tag, a fresh build from the merged `main` commit, a draft, the draft check, the Owner Release Gate (C15 BLOCKED, C16 NOT RUN, the S5 icon gaps), publication and the public check. `distribution_permitted` stays false.

**Release-5A-1 on `main`** (PR #78, [record](docs/V2_R5A1_VERSION_FREEZE.md)). The Owner approved application version `2.0.0` and the planned tag `v2.0.0`. `pyproject.toml` and `__version__` say `2.0.0`, and both installer profiles derive their names from it (`STI-2.0.0-x64-setup.exe` for the candidate profile). V1 `0.10.0` and the Release-4B records are history. A private preliminary candidate was built from a clean committed PR revision and checked; it is not the release installer, because that revision is squash-merged away. After independent review and a separate Owner merge authorization, a fresh build from the resulting `main` commit is required. The tag `v2.0.0`, any Draft or Release and public distribution are not authorized or created. B1 stays OPEN, `distribution_permitted` false, C15, C16 and the S5 icon gaps unchanged.

