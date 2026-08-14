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

## Current lifecycle phase

**Current phase: Release Candidate**

Feature Complete Review is completed, Feature Freeze is PASS, Product
Hardening is complete, and Full Regression and Manual Acceptance is PASS.
Release Candidate work has not started, and release readiness remains No.
Findings belong in the
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

**Status: Current phase. Not started.**

An RC decision freezes the candidate contents and verifies:

- version and package metadata;
- clean installation and reproducible local startup;
- supported Python environments;
- model revision and optional dependency behavior;
- licenses, attribution, and notices;
- final privacy and repository-hygiene review;
- full automated and manual regression;
- documented release blockers and their disposition.

An RC label does not automatically imply `1.0.0`, production readiness, public
hosting, or public release. Version and delivery decisions require their own
explicit gate.

## Deferred next-version backlog

The following remain outside current-version hardening:

- transcript and long-form analysis;
- French or multilingual capability;
- platform connectors;
- local persistence;
- accounts, shared workspaces, or cloud services;
- additional models, input domains, and top-level workflows;
- other product expansions classified as deferred by the feature audit.

Deferred items are reviewed only after the current release-candidate decision
or after an explicit Feature Freeze reopening. They must not be mixed into
current-version defect or hardening work.
