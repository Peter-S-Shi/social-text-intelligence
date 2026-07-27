# Project Status

This file is the canonical source of current project state. The
[Roadmap](ROADMAP.md) defines lifecycle phases and mutable planning; the
[Project Charter](PROJECT_CHARTER.md) defines stable product and engineering
principles.

| Field | Current state |
| --- | --- |
| Project | Social Text Intelligence |
| Current version | `0.10.0` |
| Reviewed baseline main SHA | `c746bccda39e7a93ae681f22adf57be51cba5b87` |
| Current validated candidate | PR #13 head (authoritative SHA in GitHub); governance correction began from reviewed head `823fa481aad25448160891ff7f2dfc15f2f389fa` |
| Current lifecycle phase | **Feature Complete Review** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | Not completed |
| Feature Freeze status | Not started |
| Product Hardening status | Not started |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | No blockers classified yet; manual audit pending |
| Approved audit items | None yet |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Lifecycle-alignment branch: 118 tests passed, 2 opt-in model tests skipped; Ruff passed; strict MyPy passed for 65 files; compileall passed; pip check passed; documentation links and static QA artifact checks passed |
| Next required action | Execute the manual feature-complete audit |
| Last updated | 2026-07-27 |

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
[Manual QA artifact](manual_review_questionnaire.html).
