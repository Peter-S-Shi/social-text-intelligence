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
| Product Hardening Batch A4 merged main SHA | `5778f8f8804c3014f16940af1d7254c202dbcf41` — PR #21 merged; A5 synchronized baseline |
| Product Hardening Batch A5 behavioral candidate SHA | `a3ec11b674c11148d66be73475b43d0796329a54` — current-state mutation/concurrency integrity review PASS; behavioral-head CI PASS |
| Product Hardening Batch A5 merged main SHA | `3a0bb9c9460379b55a6488f966034419e40cf91d` — PR #22 merged; A6 synchronized baseline |
| Product Hardening Batch A6 behavioral candidate SHA | `1a2d25fafc532215b45cf8d6310e8e1b2b16140d` — Host/same-origin/CSP/security-header review, behavioral-head CI, and real-browser smoke PASS |
| Product Hardening Batch A6 merged main SHA | `cfcd13ef582996b8c75aa20524dcc212e2ab8922` — PR #23 merged; A7 synchronized baseline |
| Product Hardening Batch A7 behavioral candidate SHA | `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` — lifecycle/CLI consistency implementation and review PASS |
| Product Hardening Batch A7 reviewed head SHA | `371b41bec0c6418bc07748a36d34e46dd4392664` — PR #24 final-head Python 3.11/3.12/3.13 CI PASS |
| Product Hardening Batch A7 merged main SHA | `e73ed30c54b78630fd9bae7193119868277ca70a` — PR #24 merged; A8 synchronized baseline |
| Product Hardening Batch A8 behavioral candidate SHA | `577bb3d09cb02eeebc36133cd5ce408d5fae4a20` — accessibility semantics and keyboard-recovery implementation |
| Product Hardening Batch A8 reviewed head SHA | `41bd13118b77b1c35a58f72f9bd68189afc04df3` — PR #25 remote CI PASS; code review and final keyboard smoke PASS |
| Product Hardening Batch A8 governance closure | Project Status-only closure after the reviewed head; no product/test behavior change |
| Product Hardening Batch A8 merged main SHA | `75c323bb998f47262dfbd8f69ab90bf1998e92fa` — PR #25 merged 2026-08-14T05:50:26Z; baseline for any future Product Hardening batch |
| Current lifecycle phase | **Product Hardening** |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | **Completed** |
| Feature Freeze status | **PASS — explicitly approved 2026-08-13** |
| Product Hardening status | **Batches A1–A8 merged**; FCR-027, FCR-030, and FCR-045–050 are `VERIFIED`; FCR-042 and FCR-043 remain non-blocking backlog |
| Manual Acceptance status | Not started |
| Release Candidate status | Not started |
| Release readiness | **No** |
| Open blockers | PH-009 is closed as FCR-027 `VERIFIED`; PH-010 is not started |
| Approved audit items | FCR-027 reconciles PH-009 and is `VERIFIED` on behavioral SHA `577bb3d09cb02eeebc36133cd5ce408d5fae4a20`; FCR-030 reconciles PH-008 and remains `VERIFIED` on behavioral SHA `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c`; FCR-045 reconciles PH-001/PH-002 and remains `VERIFIED`; FCR-046 reconciles PH-003 and remains `VERIFIED`; FCR-047 reconciles PH-004 and remains `VERIFIED`; FCR-048 reconciles PH-005 and remains `VERIFIED`; FCR-049 reconciles PH-006 and remains `VERIFIED`; FCR-050 reconciles PH-007 and remains `VERIFIED` on behavioral SHA `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`; FCR-036 remains separately `VERIFIED`; FCR-042–043 remain `OPEN` non-blocking Product Hardening backlog |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | Product Hardening Batch A8 behavioral SHA `577bb3d09cb02eeebc36133cd5ce408d5fae4a20`: 6 focused accessibility regressions passed; full suite 172 passed with 2 opt-in model integrations skipped; Ruff, strict MyPy for 73 files, compileall, pip check, CSP/security regression, template/static checks, and repository privacy/safety checks passed. PR #25 reviewed head `41bd13118b77b1c35a58f72f9bd68189afc04df3` remote CI PASS. Real-browser evidence covers Direct validation focus and real-model success, Batch/Review/Insights/note; user keyboard-only smoke for Moderation and Triage PASS with visible focus, no keyboard trap, and recoverable errors. PR #25 merged to main SHA `75c323bb998f47262dfbd8f69ab90bf1998e92fa` |
| Next required action | Batch A8 is merged; PH-009 is closed. Do not start PH-010 or scope any further Product Hardening batch without separate authorization |
| Last updated | 2026-08-14 |

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
