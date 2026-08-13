# Project Status

This file is the canonical source of current project state. The
[Roadmap](ROADMAP.md) defines lifecycle phases and mutable planning; the
[Project Charter](PROJECT_CHARTER.md) defines stable product and engineering
principles.

| Field | Current state |
| --- | --- |
| Project | Social Text Intelligence |
| Current version | `0.10.0` |
| Reviewed baseline main SHA | `d896c4791653e674919c57e643362d90ebbcf317` |
| Current validated revision | PR #14 merged into `main` at `d896c4791653e674919c57e643362d90ebbcf317` |
| Current lifecycle phase | **Feature Complete Review** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | Not completed |
| Feature Freeze status | Not started |
| Product Hardening status | Not started |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | No release blocker classified yet; manual audit pending |
| Approved audit items | `FCR-033` local model-cache hardening is verified; no product behavior or model revision changed |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | PR #14 candidate: 119 tests passed, 2 opt-in model tests skipped; 2 real offline model integration tests passed separately; Ruff, strict MyPy for 65 files, compileall, pip check, documentation links, HTML syntax/duplicate-ID checks, and diff checks passed. PR and post-merge `main` CI passed on Python 3.11, 3.12, and 3.13 |
| Next required action | Continue the manual Feature Complete Review |
| Last updated | 2026-08-09 |

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
