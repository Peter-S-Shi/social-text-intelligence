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
| Current validated candidate | Draft PR #16 on `hardening/pre-freeze-manual-qa`; FCR-044 implementation `67eaa33` and Windows launcher `e6c176c`, with status-only follow-up at the final PR head |
| Current lifecycle phase | **Feature Complete Review** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | Manual review completed; classified corrections implemented; candidate-specific retest pending |
| Feature Freeze status | Not started |
| Product Hardening status | Not started; this branch is limited to approved pre-freeze corrections |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | FCR-044 global return-navigation correction requires manual retest on the new PR head; FCR-002 navigation verification and V-01 exact final-candidate evidence remain open. Feature Freeze still requires explicit approval |
| Approved audit items | FCR-034–041 passed delegated manual/technical retest; FCR-044 is an `IMPLEMENTED` pre-freeze blocker pending manual retest; FCR-042–043 remain `OPEN` non-blocking Product Hardening findings; FCR-033 remains `VERIFIED` |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Candidate through launcher implementation `e6c176c`: targeted launcher regression 1 passed; full suite 127 passed and 2 opt-in real-model tests skipped; Ruff passed; strict MyPy passed for 67 files; compileall, pip check, documentation links, diff checks, and privacy scan passed. GitHub CI remains authoritative for the final PR head |
| Next required action | Push the launcher and status update to Draft PR #16, confirm CI, then manually retest the one-click launcher and FCR-044 home navigation on the exact new head; do not pass Feature Freeze automatically |
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
