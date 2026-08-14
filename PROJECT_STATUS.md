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
| Product Hardening baseline main SHA | `421b0fb2610de98f09c8acec5a9e2f137f35f4e2` — stable baseline for the independent Product Hardening cycle |
| Tested behavioral SHA | `16acb0f5931b022b57f0c5cdbe4501973aa3ad11` — candidate-specific final-head smoke test PASS |
| Governance closure SHA | `2a701f87b167d5a112184b1ffedb4f8f7a12d95e` — documentation-only closure; it does not replace the tested behavioral SHA |
| Product Hardening Batch A1 tested behavioral SHA | `729318c6c253ea8eee8351e766bbcfe7a335c297` — PR #18 correction head; remote CI PASS |
| Product Hardening Batch A1 merged main SHA | `1b36fe8c024823c1f4829621a7bcc733b2915c93` — PR #18 merged; A2 synchronized baseline |
| Product Hardening Batch A2 behavioral candidate SHA | `31b5e6cf7fc6d551bb72680900976595008d9d7c` — complete-input inference contract and targeted regressions |
| Product Hardening Batch A2 merged main SHA | `1c9764ba7bcd45b07a07a93077b86070e358a0ab` — PR #19 merged; A3 synchronized baseline |
| Product Hardening Batch A3 behavioral candidate SHA | `def0577feb3c43d4e9e81577003c43da821b6ba2` — global HTTP request-body boundary and targeted regressions |
| Product Hardening Batch A3 merged main SHA | `552be0012300ce0d40714b739bbb9e27248c8bca` — PR #20 merged; A4 synchronized baseline |
| Product Hardening Batch A4 evidence | FCR-048 `VERIFIED` — real offline 1/50/500-row CPU probe; no product behavior change required |
| Current lifecycle phase | **Product Hardening** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | **Completed** |
| Feature Freeze status | **PASS — explicitly approved 2026-08-13** |
| Product Hardening status | **Batches A1–A3 merged; Batch A4 evidence sufficient and awaiting Draft PR review**; FCR-045–048 are `VERIFIED`; FCR-042 and FCR-043 remain non-blocking backlog |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | PH-005 evidence is sufficient and no corrective work is required; PH-006 remains unstarted and outside Batch A4 |
| Approved audit items | FCR-045 reconciles PH-001/PH-002 and remains `VERIFIED`; FCR-046 reconciles PH-003 and remains `VERIFIED`; FCR-047 reconciles PH-004 and remains `VERIFIED`; FCR-048 reconciles PH-005 and is `VERIFIED` by the real-model capacity probe; FCR-036 remains separately `VERIFIED`; FCR-042–043 remain `OPEN` non-blocking Product Hardening backlog |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Product Hardening Batch A4: real offline CPU probe completed 1/50/500 rows with 1/50/500 successes, zero failures, 0.075/3.763/39.636-second warm times, 12.61 rows/s at 500, 1,061,908,480-byte peak RSS, and active-lease commit across a 1-second probe TTL; full suite 148 passed and 2 opt-in integration tests skipped; Ruff, strict MyPy for 69 files, compileall including the benchmark, and pip check passed |
| Next required action | Review the Batch A4 Draft PR and its FCR-048 evidence; do not start PH-006 without a separately authorized hardening batch |
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
