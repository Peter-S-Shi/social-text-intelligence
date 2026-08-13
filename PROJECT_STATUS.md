# Project Status

This file is the canonical source of current project state. The
[Roadmap](ROADMAP.md) defines lifecycle phases and mutable planning; the
[Project Charter](PROJECT_CHARTER.md) defines stable product and engineering
principles.

| Field | Current state |
| --- | --- |
| Project | Social Text Intelligence |
| Current version | `0.10.0` |
| Reviewed baseline main SHA | `dc70857ffef7e63997376b97510ab62389a20c41` |
| Current validated candidate | Draft PR #16 on `hardening/pre-freeze-manual-qa`; validated implementation commit `31c16c0`, with status-only follow-up at the current PR head |
| Current lifecycle phase | **Feature Complete Review** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | Manual review completed; classified corrections implemented; candidate-specific retest pending |
| Feature Freeze status | Not started |
| Product Hardening status | Not started; this branch is limited to approved pre-freeze corrections |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | Candidate-specific manual retest for FCR-034, FCR-036, FCR-039, FCR-040, and FCR-041; V-04 workspace-derived Triage privacy opt-ins; V-01 exact final candidate evidence. Feature Freeze still requires explicit approval |
| Approved audit items | FCR-034–041 are `IMPLEMENTED / Keep and harden`; FCR-042–044 are `OPEN` non-blocking Product Hardening findings; FCR-033 remains `VERIFIED` |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Draft PR #16 implementation `31c16c0`: targeted hardening/QA regression 34 passed; full suite 125 passed and 2 opt-in real-model tests skipped; Ruff passed; strict MyPy passed for 66 files; compileall, pip check, documentation links, questionnaire HTML parsing/duplicate-ID checks, diff checks, and privacy scan passed. GitHub PR checks are authoritative for the current head |
| Next required action | Confirm Draft PR #16 CI, then manually retest the listed blocker and privacy items on the exact PR head; do not pass Feature Freeze automatically |
| Last updated | 2026-08-13 |

## Required maintenance

Every coherent feature-review, freeze-gate, hardening, full-regression,
manual-acceptance, release-candidate, or delivery change must update this file.
The update must identify the reviewed baseline, tested candidate revision,
current phase, gate status, blockers, audit dispositions, latest validation,
and next required action. The actual merged `main` SHA should be recorded in
the next lifecycle-status update after merge; a PR base SHA must never be
presented as a future `main` SHA.

Historical implementation detail belongs in [DEVLOG.md](DEVLOG.md). Feature
scope decisions belong in the
[Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md). Repeated
human test results should be exported from the canonical
[Manual QA artifact](manual-qa/manual_review_questionnaire.html).
