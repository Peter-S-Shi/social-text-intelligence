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
| Product Hardening Batch A8 merged main SHA | `75c323bb998f47262dfbd8f69ab90bf1998e92fa` — PR #25 merged 2026-08-14T05:50:26Z |
| Post-A8 governance sync merged main SHA | `7ef4d29d2bb98af2a60003748a575de8c5bcda96` — PR #26 merged; A9 synchronized baseline |
| Product Hardening Batch A9 behavioral candidate SHA | `076fbe4f883073a1961b024d52d06d9cac22a58a` — Triage timestamp ordering integrity under FCR-051; targeted/full local validation and real-browser smoke PASS |
| Product Hardening Batch A9 reviewed head SHA | `ef9b54adc3eeed98ef4154f71ae7f69e5f6000cb` — PR #27 formal review PASS; final-head remote CI PASS |
| Product Hardening Batch A9 merged main SHA | `3fecf5ce43939045ed7100915eca41b9e5b2c64e` — PR #27 merged; A10 synchronized baseline |
| Product Hardening Batch A10 behavioral candidate SHA | `c1feb67e1b40742c7f34104e5f0922d67498dd12` — Applied filter/sort/selection state reflection integrity under FCR-052; targeted/full local validation and real-browser smoke PASS |
| Product Hardening Batch A10 reviewed head SHA | `6c649dc78c18921937a2d6b49e52a94cc7e92d94` — PR #28 formal review PASS; final-head remote CI PASS |
| Product Hardening Batch A10 merged main SHA | `fc230c587c245cdb1cd75b399c91eb38ac82d768` — PR #28 merged; post-merge main CI PASS; Product Hardening closure baseline |
| Manual Acceptance Gate Standard | Established at [`docs/MANUAL_ACCEPTANCE_GATE.md`](docs/MANUAL_ACCEPTANCE_GATE.md); canonical questionnaire upgraded to v3.0 (5 new items covering FCR-051, FCR-052, and A8 accessibility semantics; carried-forward pre-freeze FCR coverage mapped) |
| Product Hardening closure merged main SHA | `67aad7686c40d136c2646dfc6d5699f8a4912713` — PR #29 merged; lifecycle phase transitioned to Full Regression and Manual Acceptance |
| Manual Acceptance readiness merged main SHA | `71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1` — PR #30 merged (Gate Standard + questionnaire v3.0 + FCR-003 Direct acceptance-item correction); independent post-merge `main` CI PASS on Python 3.11/3.12/3.13; tested candidate SHA for Manual Acceptance execution below |
| Manual Acceptance execution | **PASS** — repository-owner-authorized agent-operated session on tested SHA `71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1`; 20/20 repository-owner-defined required fresh-interaction profile items PASS (0 FAIL, 0 blocking defects); FCR-042/FCR-043 dispositions untouched; all nine carried-forward pre-freeze FCRs (003/005/014/015/017/021/023/026/031) formally reconciled and closed `VERIFIED` in the same decision; evidence exported to `manual-qa/results/sti-full-regression-manual-acceptance-71fa608-2026-08-14.{json,md}` (local-only, gitignored, not committed) |
| Automated Full Regression evidence | Reused exact-SHA post-merge CI on `71fa608ec523ecc17b160568c6b4ffcd0a7b0fd1` (pytest, Ruff, MyPy, compile, dependency install — PASS on Python 3.11/3.12/3.13) plus existing Product Hardening real-model/concurrency/HTTP-boundary/browser-security evidence; no duplicate local re-run performed |
| RC candidate SHA | `427984a5d39b7e20eafc53e588aa5a53b6bd320d` — PR #31 merged; independent post-merge `main` CI PASS on Python 3.11/3.12/3.13; differs from Manual Acceptance tested SHA `71fa608...` only by governance/docs/lifecycle-test changes (verified by diff), so Manual Acceptance runtime evidence remains valid without retest |
| RC package identity | `social-text-intelligence` `0.10.0`, `Requires-Python >=3.11`, console scripts `sti`/`sti-web`, extras `sentiment`/`emotion`/`web`/`dev` — confirmed in both `pyproject.toml` and the built wheel's `METADATA`/`entry_points.txt`; version not changed to `1.0.0` or a prerelease tag |
| RC wheel build/artifact result | **PASS** — built `social_text_intelligence-0.10.0-py3-none-any.whl` from a clean detached worktree at the candidate SHA; contents verified complete (13 templates, 5 static files, 4 packaged JSON resources, `LICENSE`) and clean (no tests, caches, model weights, private data, or machine paths) |
| RC clean core install result | **PASS** — fresh venv, no-extras wheel install: `pip check` clean, installed version reports `0.10.0`, `sti about` and `sti contracts` both work |
| RC clean web-extra install/startup result | **PASS** — fresh venv, `[web]` extra install: `sti-web --help` works; server binds to `127.0.0.1` only (confirmed via `netstat`, not `0.0.0.0`); installed-wheel home page and `/static/app.css` both return 200, proving templates/static were actually packaged |
| RC missing-model-extras behavior | **PASS** — with no `sentiment`/`emotion` extras installed, a Direct analysis submission returns HTTP 200 with a clear in-page error ("Local model dependencies are not installed. Install the model extras.") and `role="alert"`; no 500, no traceback, no internal path exposed |
| RC supported-Python evidence | Reused exact-SHA CI on Python 3.11/3.12/3.13 (all green); local wheel smoke performed on the locally available Python 3.12 only, per RC efficiency rule |
| RC model pin/offline contract result | **PASS** — candidate source pins match approved records exactly (`cardiffnlp/twitter-roberta-base-sentiment-latest@3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`, `SamLowe/roberta-base-go_emotions@d75048347613a25d77de8cf6412eaae9fa7b26be`), passed as explicit non-floating `revision=` arguments; no weights bundled in the wheel; model/runtime dependencies remain optional extras |
| RC license/attribution/notices result | **PASS** — `LICENSE` (MIT), `THIRD_PARTY_NOTICES.md`, `pyproject.toml`, and wheel `METADATA` are mutually consistent: Flask (BSD-3-Clause), PyTorch/Transformers, and both models' license/revision/provenance are recorded and match code exactly; no redistribution-of-weights claim contradicted |
| RC privacy/repository/package hygiene result | **PASS** — `.gitignore` protects `dist/`, `build/`, `model_cache/`, `manual-qa/results/`, `.env`, `.pytest_cache/`; `.prompt-drafts/` excluded via `.git/info/exclude` and untracked; no weights/databases/credentials/secrets found in tracked files; built wheel contains no unrelated local artifacts |
| Release Candidate Gate | **PASS — 2026-08-14.** All RC criteria met; no release blocker found; no packaging correction was needed. Does not imply `1.0.0`, production readiness, public hosting, a GitHub Release, or release readiness Yes |
| Current lifecycle phase | **Public Portfolio Delivery** — Release Candidate Gate is **PASS**; the repository owner's Version / Delivery Decision approved public portfolio delivery of `0.10.0` |
| Feature milestone status | Milestones 1–10 complete |
| Feature Complete Review status | **Completed** |
| Feature Freeze status | **PASS — explicitly approved 2026-08-13** |
| Product Hardening status | **COMPLETE — Batches A1–A10 merged**; FCR-027, FCR-030, and FCR-045–052 are `VERIFIED`; PH-001–PH-010 are all resolved; FCR-042 and FCR-043 remain explicitly accepted `OPEN` non-blocking backlog |
| Manual Acceptance status | **PASS — 2026-08-14, 20/20 required items, 0 blocking defects** |
| Release Candidate status | **PASS — 2026-08-14** |
| Public portfolio delivery | **Yes — approved by the repository owner, 2026-08-15.** This resolves the previously pending Version / Delivery Decision for public portfolio delivery specifically; GitHub repository visibility is public. No version tag or GitHub Release has been created, and none is implied by this decision |
| Open blockers | None. PH-001–PH-010 are all closed under FCR-045–051; FCR-052 is a separately discovered, closed, non-blocking finding. FCR-042/FCR-043 are explicitly accepted non-blocking backlog, not release blockers. All nine pre-freeze "OPEN verification" checklist items (FCR-003, 005, 014, 015, 017, 021, 023, 026, 031) were formally reconciled and closed `VERIFIED` during Full Regression and Manual Acceptance on 2026-08-14, using existing Feature Freeze/Product Hardening/regression-test evidence plus this session's own fresh evidence where directly applicable (FCR-003, FCR-026); none carries into Release Candidate unresolved |
| Approved audit items | FCR-027 reconciles PH-009 and is `VERIFIED` on behavioral SHA `577bb3d09cb02eeebc36133cd5ce408d5fae4a20`; FCR-030 reconciles PH-008 and remains `VERIFIED` on behavioral SHA `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c`; FCR-045 reconciles PH-001/PH-002 and remains `VERIFIED`; FCR-046 reconciles PH-003 and remains `VERIFIED`; FCR-047 reconciles PH-004 and remains `VERIFIED`; FCR-048 reconciles PH-005 and remains `VERIFIED`; FCR-049 reconciles PH-006 and remains `VERIFIED`; FCR-050 reconciles PH-007 and remains `VERIFIED` on behavioral SHA `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`; FCR-036 remains separately `VERIFIED`; FCR-051 reconciles PH-010 and is `VERIFIED` on behavioral SHA `076fbe4f883073a1961b024d52d06d9cac22a58a` (reviewed head `ef9b54adc3eeed98ef4154f71ae7f69e5f6000cb`); FCR-052 is `VERIFIED` on behavioral SHA `c1feb67e1b40742c7f34104e5f0922d67498dd12` (reviewed head `6c649dc78c18921937a2d6b49e52a94cc7e92d94`), a non-blocking independent applied-state reflection root cause found outside the original PH-001–010 list; FCR-003/005/014/015/017/021/023/026/031 (carried-forward pre-freeze verification items) are all `VERIFIED` as of the 2026-08-14 Full Regression and Manual Acceptance decision in the Feature Complete Manual Audit; FCR-042–043 remain `OPEN` non-blocking Product Hardening backlog, explicitly accepted and not required for this closure |
| Deferred next-version items | Transcript/long-form analysis; French capability; platform connectors; persistence; other approved future expansions |
| Latest validation | RC candidate SHA `427984a5d39b7e20eafc53e588aa5a53b6bd320d`: reused independent post-merge `main` CI PASS on Python 3.11/3.12/3.13 (PR #31) plus reused Manual Acceptance evidence from `71fa608...` (governance-only diff verified), plus freshly generated packaging/install/startup evidence for this RC Gate (wheel build, clean core install, clean web-extra install/startup, missing-extras behavior, model-pin/license/hygiene reconciliation). All ten Batch A1–A10 behavioral/reviewed heads passed their own targeted and full regression, formal review, and remote CI in turn (see PR #18–#28) |
| Next required action | None for public portfolio delivery — the Version / Delivery Decision is resolved and the repository is public. A future version tag or GitHub Release remains a separate, independent decision that has not been made and is not required by this closure |
| Last updated | 2026-08-15 (Public Portfolio Delivery — Version / Delivery Decision resolved) |

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
