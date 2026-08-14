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
| Tested behavioral SHA | `16acb0f5931b022b57f0c5cdbe4501973aa3ad11` — candidate-specific final-head smoke test PASS |
| Governance closure SHA | `2a701f87b167d5a112184b1ffedb4f8f7a12d95e` — documentation-only closure; it does not replace the tested behavioral SHA |
| Current lifecycle phase | **Product Hardening** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | **Completed** |
| Feature Freeze status | **PASS — explicitly approved 2026-08-13** |
| Product Hardening status | Entered; FCR-042 and FCR-043 retained as non-blocking backlog |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | None for Feature Freeze; release readiness remains No until Product Hardening and later gates complete |
| Approved audit items | FCR-044 manual retest passed and FCR-002 navigation verification is closed; V-01 is satisfied by the exact tested behavioral SHA; FCR-042–043 remain `OPEN` non-blocking Product Hardening backlog |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Tested behavioral SHA `16acb0f5931b022b57f0c5cdbe4501973aa3ad11`: final-head smoke test PASS; full suite 127 passed and 2 opt-in real-model tests skipped; Ruff, strict MyPy for 67 files, compileall, pip check, documentation links, diff/privacy checks, and GitHub CI on Python 3.11/3.12/3.13 passed |
| Next required action | Confirm PR #16 final-head CI, mark Ready for Review, and wait for explicit merge approval before beginning Product Hardening work |
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
