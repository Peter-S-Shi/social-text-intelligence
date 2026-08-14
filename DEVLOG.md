# Development Log

## Product Hardening Batch A10 — Applied filter/sort/selection state reflection integrity

Product Hardening Batch A9 / PR #27 is recorded as merged to main at SHA
`3fecf5ce43939045ed7100915eca41b9e5b2c64e`; FCR-051 remains `VERIFIED`.

A read-only audit of every GET filter/sort form in the interface (Triage
Workspace and Guide, Review, Batch, both Insights view forms, Moderation
Prepare) found that Review, Batch, the Insights explorer view, and Triage
Guide's built-in ticket filter already reflected applied query state
correctly, while three surfaces did not: Triage Workspace's 11 select
controls and its `q` text-search input, Moderation Prepare's 5 select
controls (whose route did not even pass the parsed filters into the
template), and Insights Representative Cases' `record_id` checkboxes,
which genuinely determine the result in `user_selected` mode but were
never checked. None of this is covered by FCR-027 (keyboard/accessibility
semantics, already `VERIFIED` with an explicitly narrower scope), FCR-029
(error/empty-state recovery — nothing here errors), or FCR-030
(documentation consistency, not runtime UI), and it is not folded into
FCR-042 or FCR-043. New permanent `FCR-052` is created, classified
`HARDENING`, non-blocking.

All three surfaces now use the same native Jinja `selected`/`checked`/
`value` pattern already proven correct elsewhere in the codebase. Moderation
Prepare's route passes its existing `CaseFilter` into the template instead
of building a second parser. Insights checkbox reflection is deliberately
gated to `example_mode is ExampleMode.USER_SELECTED`, since `record_id` has
no effect in any other mode and reflecting it unconditionally would falsely
imply a stale, non-effective query parameter was still driving the result.
No filtering, sorting, or selection logic changed, and the FCR-051 timestamp
sort algorithm is untouched.

Fourteen targeted regressions cover: enum/boolean/text-search filters that
narrow the Triage result while the matching control shows `selected`/
`value`; the default no-query view showing no unexpected non-default state;
Moderation difficulty and tri-state safety-sensitive filters narrowing the
built-in case library while reflecting correctly, including a combined
non-default case; Insights `user_selected` mode checking exactly the
submitted records and excluding others; and a non-selecting example mode
correctly leaving `record_id` unchecked, proving the effective-state gate.
Eleven of the fourteen fail against the pre-fix implementation. The complete
suite passed 195 tests (14 more than the A9 baseline) with 2 opt-in model
integrations skipped; Ruff, strict MyPy for 75 files, compileall, and pip
check passed, and the 9 FCR-051 targeted regressions were unaffected.

A real-browser smoke drove the actual Triage workspace-creation, ticket,
Moderation workspace-creation, and Batch-to-Insights paths. Applying
`status=finalized` and `sort=urgency` in Triage Workspace left only the
finalized ticket visible with both controls genuinely selected. Applying
`difficulty=beginner` and `safety_sensitive=false` in Moderation Prepare
narrowed the case library to exactly the three matching built-in cases with
both controls genuinely selected. Selecting two records in Insights
Representative Cases under `user_selected` mode left exactly those two
checkboxes checked after submission. Behavioral candidate:
`c1feb67e1b40742c7f34104e5f0922d67498dd12`. FCR-052 is `IMPLEMENTED` pending
PR review. FCR-042 and FCR-043 remain open non-blocking, and Feature Freeze
remains PASS.

## Product Hardening Batch A9 — Triage timestamp ordering integrity

Reconciled Phase 0 PH-010 as new permanent `FCR-051`. Existing FCR-015 and
FCR-038 govern Context Note UTC display, FCR-042 governs score-list ordering,
and FCR-043 governs visual hierarchy; none defines the timestamp-ordering root
cause, so a new permanent ID was created rather than stretching an existing
one. The post-A8 governance sync PR #26 is recorded as merged at main SHA
`7ef4d29d2bb98af2a60003748a575de8c5bcda96`, the baseline for this batch.

The Support Triage `Sort: Timestamp` control sorted the stored ISO timestamp as
a raw string. Batch CSV accepts any valid ISO 8601 value and keeps its stated
offset (or its unspecified-timezone status) rather than normalizing it, so one
workspace can hold several offsets at once, and lexicographic order is not
real-instant order: `2026-07-01T08:00:00-05:00` is 13:00Z but sorts as text
before `2026-07-01T10:00:00+00:00`, which is 10:00Z. The wrong order was
silent, and the branch had no test coverage.

Ordering now parses the value and applies one explicit contract. Offset-aware
timestamps sort first, ascending by real instant. Timezone-unspecified values
are never assigned a zone; they form a separate later bucket ordered by stated
wall-clock value. Missing or unparsable values sort last. `original_order`
breaks every tie, and because the leading bucket always differs, values from
different buckets are never compared with each other. Aware values keep their
original offset and rely on native instant comparison instead of
`astimezone(UTC)`, which raises `OverflowError` on parsable extremes such as
`9999-12-31T23:59:59-14:00` and would otherwise crash the page.

Nothing about timestamp truth changed. The accepted Batch input range,
`NormalizedTextInput.timestamp`, Review display, Triage trusted metadata, the
Batch/Insights/Triage export representation, and system-generated UTC audit
timestamps are all untouched, and user timestamps are still never normalized to
UTC. `docs/CONTRACTS.md` now states the sort contract, the boundary between
user timestamps and system audit timestamps, and the unchanged Insights
month/date grouping semantics. The workspace sort control carries associated
help text so the interface does not imply that timezone-unspecified and
offset-aware values share one timeline.

Nine targeted regressions cover instant-versus-string ordering, the stable
tie-break for one instant spelled with two offsets, naive wall-clock ordering,
the mixed-bucket contract, missing-last ordering, extreme-offset safety,
non-interference with the other sort modes, and preservation of stored values.
Five of them fail against the pre-fix implementation, and the extreme-offset
case fails against an `astimezone` variant. The complete suite passed 181 tests
with 2 opt-in model integrations skipped; Ruff, strict MyPy for 74 files,
compileall, and pip check passed.

A real-browser smoke drove the actual Batch upload, analysis, workspace-ticket,
and `Sort: Timestamp` path with a synthetic batch holding two different
offsets, one timezone-unspecified timestamp, and one missing timestamp. The
rendered order was 10:00Z, 13:00Z, timezone-unspecified 1999, then missing; the
other sort modes were unaffected; and every stored timestamp remained its
original text with no conversion. Behavioral candidate:
`076fbe4f883073a1961b024d52d06d9cac22a58a`. FCR-051 is `IMPLEMENTED` pending
PR review. FCR-042 and FCR-043 remain open non-blocking, and Feature Freeze
remains PASS.

PR #27 formal review subsequently passed on reviewed head
`ef9b54adc3eeed98ef4154f71ae7f69e5f6000cb`, which also passed final-head CI on
Python 3.11, 3.12, and 3.13. FCR-051 is therefore `VERIFIED` and PH-010 is
closed; FCR-027, FCR-030, and FCR-045–050 remain `VERIFIED`, Feature Freeze
remains PASS, FCR-042/043 remain `OPEN` non-blocking, and the parked
filter/select applied-state finding remains a separate, unresolved item outside
FCR-051.

## Product Hardening Batch A8 — accessibility semantics and keyboard recovery

Reconciled Phase 0 PH-009 with existing FCR-027 rather than creating FCR-051.
The 2026-08-13 `VERIFIED / Keep as-is` keyboard smoke remains historical
evidence. A deeper Product Hardening audit found material semantic gaps, so
FCR-027 is revalidated as class `HARDENING`, decision `Keep and harden`, status
`IMPLEMENTED` pending PR review and final manual keyboard smoke. Product
Hardening Batch A7 / PR #24 is recorded as merged at main SHA
`e73ed30c54b78630fd9bae7193119868277ca70a`; FCR-030 remains `VERIFIED` and
Feature Freeze remains PASS.

Every complete server-rendered page now provides a visible-on-focus skip link
to a focusable main landmark. Active primary navigation and workflow steps use
`aria-current`; Direct validation associates its alert and help with the text
field and restores focus there, while workflow-level errors restore focus to a
focusable alert. Key helper text is programmatically associated with Batch,
Review, Insights, Moderation, and Triage controls. Batch analysis publishes a
labelled progress status and sets `aria-busy` during submission. Representative
data tables now declare column and row header scope. Native controls remain in
place, summary joins the existing visible-focus rule, and no positive tabindex,
faux button, dependency, workflow redesign, or CSP relaxation was introduced.

Six focused accessibility regressions cover skip targets, current-page/step
semantics, labels/help/errors, focus-recovery markup, Batch running state,
explicit table headers, and keyboard anti-pattern scans. The complete suite
passed 172 tests with 2 opt-in model integrations skipped. Ruff, strict MyPy for
73 files, compileall, pip check, CSP/security regressions, static checks, and
repository privacy/safety checks passed.

Real-browser smoke passed Direct validation focus recovery and real-model
success, Batch preview/analysis, Human Review acceptance, Insights navigation,
note creation, and note-error focus recovery. The local browser-control
security boundary interrupted the remaining Moderation/Triage browser session;
those final keyboard-only flows remain explicitly assigned to user retest.
Behavioral candidate: `577bb3d09cb02eeebc36133cd5ce408d5fae4a20`.
FCR-043 remains open for visual information hierarchy, and PH-010 is not
started.

The user's final keyboard-only smoke subsequently passed for Moderation and
Support Triage, with no keyboard trap, a visible focus indicator, and
recoverable validation errors. Reviewed PR #25 head
`41bd13118b77b1c35a58f72f9bd68189afc04df3` passed CI on Python 3.11, 3.12, and
3.13. FCR-027 is therefore `VERIFIED` and PH-009 is closed; FCR-030 and
FCR-045–050 remain `VERIFIED`, Feature Freeze remains PASS, FCR-043 remains
`OPEN` non-blocking, and PH-010 remains unstarted and unscoped. PR #25 merged
to main at `75c323bb998f47262dfbd8f69ab90bf1998e92fa`.

## Product Hardening Batch A7 — lifecycle and CLI consistency

Reconciled Phase 0 PH-008 with existing FCR-030 rather than creating a second
permanent finding. FCR-030 is classified `HARDENING`, decision `Keep and
harden`, and remains `IMPLEMENTED` pending PR review. Product Hardening Batch
A6 / PR #23 is recorded as merged at main SHA
`cfcd13ef582996b8c75aa20524dcc212e2ab8922`; FCR-050 remains `VERIFIED` and
Feature Freeze remains PASS.

Separated current-state responsibilities to prevent recurring drift:
`PROJECT_STATUS.md` is the only canonical live execution state, `ROADMAP.md`
owns the mutable lifecycle plan, `PROJECT_CHARTER.md` owns stable product and
engineering boundaries, `README.md` provides a concise current overview, and
`docs/DEVELOPMENT.md` defines contributor discipline. Current references now
agree on version 0.10.0, Milestones 1–10 complete, Feature Complete Review
Completed, Feature Freeze PASS, Product Hardening current, Manual Acceptance
and Release Candidate not started, and release readiness No. The canonical
Manual QA link remains `manual-qa/manual_review_questionnaire.html`.

`sti about` now reports the installed version, Milestone 10 feature boundary,
and existing capabilities. It deliberately does not embed the live phase,
gate, PR, SHA, blocker, or release-readiness ledger; instead it points users to
the repository `PROJECT_STATUS.md`. Targeted regression rejects the former
feature-freeze-pending statement and prevents the CLI from duplicating current
lifecycle values.

The stale-state audit changed only current declarations and instructions.
Dated handoffs, DEVLOG entries, historical FCR evidence, and past PR records
retain statements that were accurate at the time. No model, threshold,
workflow, state, security, privacy, product-scope, or version contract changed.
PH-009 remains unstarted.

Ten focused CLI/lifecycle tests passed. The complete deterministic suite passed
167 tests with 2 opt-in model integrations skipped. Ruff, strict MyPy for 72
files, compileall, pip check, tracked-document stale-state/link/manual-QA
consistency checks, and repository privacy/safety checks passed. Behavioral
candidate `cce3133d7a2dcf9d1d06fe2e11a190c79dd22a1c` passed lifecycle/CLI
consistency review. Reviewed PR #24 head
`371b41bec0c6418bc07748a36d34e46dd4392664` passed final-head CI on Python
3.11, 3.12, and 3.13. FCR-030 is therefore `VERIFIED`; FCR-045–050 remain
`VERIFIED`, Feature Freeze remains PASS, and PH-009 remains unstarted. This
closure changes governance documentation only.

## Product Hardening Batch A6 — Local browser boundary hardening

Reconciled Phase 0 PH-007 as permanent FCR-050. Existing FCR-045–049 govern
ephemeral capacity/state, complete-input inference, request-body capacity,
real-model evidence, and concurrent mutations; none defines the browser Host,
same-origin, or response-header boundary.

Behavioral candidate `1a2d25fafc532215b45cf8d6310e8e1b2b16140d`
passed Host/same-origin/CSP/security-header code review and PR #23
behavioral-head CI on Python 3.11, 3.12, and 3.13. The user also completed a
real-browser smoke: Direct, Batch/Review, Insights distribution progress and
notes, Moderation/Triage forms, and CSV downloads operated normally, with no CSP
violation or blocked local resource in DevTools Console. FCR-050 is therefore
`VERIFIED`. This closure changes governance documentation only; FCR-049 remains
`VERIFIED`, Feature Freeze remains PASS, and no later hardening item is started.

Configured Flask trusted hosts for exactly `127.0.0.1` and `localhost`, while
the CLI continues binding only `127.0.0.1`. A fixed private 400 handles rejected
Host values before route dispatch. Unsafe methods now require an exact
same-origin Origin, or a same-origin Referer when Origin is absent; explicit
cross-origin, malformed, or `null` values receive a fixed private 403. Requests
with neither header remain supported as documented local non-browser clients
behind trusted Host validation. Rejection occurs before model inference,
request-body parsing, or workspace mutation.

All responses now receive a self-only CSP, `nosniff`,
`Referrer-Policy: same-origin`, `X-Frame-Options: DENY`, and the existing
no-store/no-cache headers. The CSP uses no wildcard, external origin, or
`unsafe-inline`. Replaced the sole dynamic inline style in Insights with a
native progress element styled by the existing local stylesheet. HSTS, CORS,
TLS, LAN binding, sessions, accounts, remote deployment, and CSP reporting are
explicitly excluded.

Focused regressions cover approved hosts, same-origin and fallback behavior,
private Host/Origin rejection before inference, preservation of Batch/Review/
Insights/Moderation/Triage state, headers on HTML/redirect/error/413/CSV/static
responses, and the absence of inline/external template resources. Selected A3
request-ceiling and A5 lease/concurrency tests remain green. Feature Freeze
remains PASS; no later PH item is started.

Twelve focused browser-boundary/A3/A5 tests passed. The complete deterministic
suite passed 163 tests with 2 opt-in model integrations skipped. Ruff, strict
MyPy for 71 files, compileall, and pip check passed.

Batch A5 / PR #22 was merged at main SHA
`3a0bb9c9460379b55a6488f966034419e40cf91d`, the synchronized A6 baseline;
FCR-049 remains `VERIFIED`.

## Product Hardening Batch A5 — Concurrent workspace mutation integrity

Reconciled Phase 0 PH-006 as permanent FCR-049. FCR-045 protects Batch
capacity, TTL, and active-analysis write-back, but it does not cover stale
read/derive/replace races across the broader process-memory workspace stores.

Behavioral candidate `a3ec11b674c11148d66be73475b43d0796329a54`
passed current-state mutation/concurrency integrity code review and PR #22
behavioral-head CI on Python 3.11, 3.12, and 3.13. FCR-049 is therefore
`VERIFIED`. This closure changes governance documentation only; FCR-048 remains
`VERIFIED`, Feature Freeze remains PASS, and PH-007 is not started.

Added one shared store-level atomic mutation primitive. Batch, Moderation, and
Triage stores now invoke each mutation against the current workspace while the
store lock is held, then save that result atomically. Independent mutations
therefore compose instead of replacing one another from stale snapshots.
One-shot rules are revalidated against current state: competing Moderation
first decisions and Triage finalization return an explicit HTTP 409 instead of
silently overwriting an accepted decision. Missing or expired workspaces retain
404 semantics, and Batch active-analysis mutations remain blocked by the A1
lease contract.

Protected mutations include Batch column selection; Human Review decisions;
persisted Insight selections and context-note add/delete; Moderation prepared
cases, sessions, decisions, feedback, cancellation, and restart; and Triage
ticket addition, draft, finalize, revise, and mock reveal. Render-only GET
navigation, filters, summaries, exports, and request-local presentation choices
remain transient because they do not replace persisted workspace state.

Deterministic nested interleaving regressions verify final saved state for
independent Review rows, Review plus Insight note, two notes, Moderation cases,
competing first decisions, separate Triage tickets, competing finalize, expiry,
and the active Batch lease. Feature Freeze remains PASS; PH-007 is not started.

Nine focused concurrency/state tests passed. The complete deterministic suite
passed 157 tests with 2 opt-in model integration tests skipped. Ruff, strict
MyPy for 70 files, compileall, and pip check passed.

Batch A4 / PR #21 was merged at main SHA
`5778f8f8804c3014f16940af1d7254c202dbcf41`, the synchronized A5 baseline;
FCR-048 remains `VERIFIED`.

## Product Hardening Batch A4 — Real-model capacity evidence

Reconciled Phase 0 PH-005 as permanent FCR-048. FCR-045 governs Batch capacity,
TTL, and active-analysis state integrity, while FCR-046 governs complete-input
inference truthfulness; neither supplied measured release evidence for the
pinned models at the 500-row product ceiling.

Added an explicit opt-in benchmark harness outside ordinary CI. It forces
offline mode, uses the existing local cache, and runs the production
`AnalysisService`, sequential `analyze_batch`, and `EphemeralBatchStore`
lease/write-back path with eight deterministic, synthetic English templates.
It records environment, cold initialization, first combined inference, warm
1/50/500-row timing and throughput, success/failure counts, process RSS, and
whether an active workspace survives and commits beyond an artificial 1-second
TTL. No `src/` product behavior, model, revision, threshold, limit, provider,
workflow, persistence, or runtime architecture changed.

On the 2026-08-14 UTC reference run (Windows 11, Python 3.12.13, Intel
i7-12700H, approximately 16 GB RAM, PyTorch 2.13 CPU-only), offline model
initialization through the first result took 3.626 seconds. Warm 1/50/500 rows
took 0.075/3.763/39.636 seconds; the 500-row stage achieved 12.61 rows/second,
with 500 successes and zero failures. Peak process RSS was 1,061,908,480 bytes
(about 0.99 GiB), while post-load growth through 500 rows was about 2.97 MiB.
The 50- and 500-row stages both exceeded the probe TTL, retained their active
lease, and committed successfully.

The evidence supports retaining `MAX_BATCH_ROWS=500` for the explicit local
synchronous workflow, with a reproducible reference RC budget documented in
`docs/REAL_MODEL_CAPACITY_EVIDENCE.md`. The budget is scoped to the checked-in
short social-text fixture and comparable CPU desktop, not presented as a
universal latency SLA. FCR-048 and PH-005 are therefore `VERIFIED`; corrective
product work is not required. Feature Freeze remains PASS, and PH-006 is not
started.

The full deterministic suite passed 148 tests with 2 opt-in integration tests
skipped. Ruff, strict MyPy for 69 files, compileall including the benchmark, and
pip check passed. PR #20 / Batch A3 was merged at main SHA
`552be0012300ce0d40714b739bbb9e27248c8bca`, the synchronized A4 baseline.

## Product Hardening Batch A3 — Global HTTP request-body boundary

Reconciled Phase 0 PH-004 as permanent FCR-047. FCR-025 covers privacy and
local-state consistency, while FCR-029 covers existing error and recovery
states; neither defines a framework-level body limit before Flask parses form
or multipart input.

The local Flask app now uses a configurable 3 MiB `MAX_CONTENT_LENGTH` request
ceiling. This is deliberately 1 MiB (50 percent) above the existing 2 MiB CSV
payload limit so multipart headers and form encoding have clear capacity. The
two limits remain independent, and configuration rejects a request ceiling
that is not greater than the CSV payload limit.

A lightweight `before_request` check rejects declared oversized bodies before
any route or temporary-state operation, including POST routes that otherwise do
not parse their bodies. Flask's request-reading limit provides the same boundary
during form/multipart parsing. One minimal 413 handler returns only fixed copy
and the configured byte limit; it never reads or echoes submitted content.
Existing `Cache-Control: no-store` and `Pragma: no-cache` response handling
continues to cover 413 responses.

Targeted regressions passed 12/12: seven boundary cases across Direct, Batch
multipart, an unparsed Batch action, Review, Insights notes, and Triage
decisions, plus five unchanged normal-flow checks. They prove no input echo, no
traceback/path disclosure, no state creation or mutation, and the independence
of the CSV byte limit. The full suite passed 148 with 2 opt-in real
model tests skipped; Ruff, strict MyPy for 69 files, compileall, and pip check
passed. Behavioral candidate:
`def0577feb3c43d4e9e81577003c43da821b6ba2`.
The user-approved code review and PR #20 pre-closure final-head CI passed, so
FCR-047 is closed as `VERIFIED` on that exact behavioral candidate. This
governance closure changes no product behavior or test.

Batch A2 was merged through PR #19 at main SHA
`1c9764ba7bcd45b07a07a93077b86070e358a0ab`; this is the synchronized A3
baseline. Feature Freeze remains PASS. PH-005 and PH-007 are not started.

## Product Hardening Batch A2 — Input truthfulness / no silent truncation

Reconciled Phase 0 PH-003 as permanent FCR-046. Existing FCR-003, FCR-006,
and FCR-008 cover input recovery, model-limit communication, and Batch partial
failure separately; none supplied the required cross-provider complete-input
success invariant.

Both pinned Transformers runtimes now encode with special tokens enabled and
`truncation=False`, then compare the real encoded sequence length with an
audited 512-token provider budget before inference. SamLowe declares 512 in its
tokenizer metadata. The pinned Cardiff tokenizer exposes the Hugging Face
unknown-limit sentinel, so the reviewed 512-token contract is explicit and
checked against the loaded model's position capacity. Incompatible finite
metadata fails closed.

Combined analysis preflights both required providers before either inference.
Direct and CLI requests return `model_input_too_long` with an explicit statement
that no truncation or partial analysis occurred. Batch isolates the failure to
the affected row, continues valid rows, and exports no model labels, scores,
identities, or revisions for the failed row. The 20,000-character application
safety ceiling remains separate. No chunking, aggregation, summarization,
model/revision/threshold change, persistence, or successful-result truncation
field was added.

Targeted complete-input regressions passed 9/9. The full suite passed 141 with
2 opt-in integration tests skipped; Ruff, strict MyPy for 69 files, compileall,
and pip check passed. A separate cached, offline run of both real-model smoke
tests passed 2/2. The user-approved code review and PR #19 final-head CI passed,
so FCR-046 is closed as `VERIFIED` on the exact behavioral candidate below.
The exact behavioral candidate is
`31b5e6cf7fc6d551bb72680900976595008d9d7c`; the following documentation
commit does not change that tested behavior.

Batch A1 was merged through PR #18 at main SHA
`1b36fe8c024823c1f4829621a7bcc733b2915c93`; this is the synchronized A2
baseline. FCR-045 remains `VERIFIED`.

## Product Hardening Batch A1 — Ephemeral Batch state integrity

Reconciled Phase 0 findings PH-001 and PH-002 as one permanent product finding,
FCR-045. FCR-036 remains the separate, already-verified confirmation contract
for user-initiated clear; FCR-045 addresses the shared Batch-store root cause:
capacity eviction and missing active-analysis write-back protection.

Batch capacity now blocks new uploads with an explicit conflict instead of
deleting existing work. Synchronous analysis acquires an exclusive in-memory
lease, remains protected from normal TTL purge and clear while active, and may
commit only through its current lease. A rejected write-back is an explicit
409 and never follows the success path. Explicit clear still releases capacity,
inactive TTL expiry remains unchanged, and no database, persistence, recovery
worker, background task, model, threshold, or privacy contract was added.

Targeted regressions cover `capacity+1`, inactive expiry, active analysis across
TTL, duplicate/stale write-back, clear conflict and recovery, and preservation
of existing Batch results, Review, Insights, and linked Triage workspaces when
a new upload is blocked.

PR #18 review found one narrow error-render regression: `/batch/upload` without
a file did not pass the configured concurrent workspace limit to `batch.html`.
Correction SHA `729318c6c253ea8eee8351e766bbcfe7a335c297` restores that context
and adds a configured-limit route regression. Targeted Batch routes passed 6/6,
the full suite passed 132 with 2 opt-in real-model tests skipped, all local
quality checks passed, and PR #18 remote CI passed on Python 3.11/3.12/3.13.
FCR-045 is therefore closed as `VERIFIED`; PH-003 remains outside this batch.

## Feature Freeze closure

Recorded the user's explicit Feature Freeze PASS for tested behavioral SHA
`16acb0f5931b022b57f0c5cdbe4501973aa3ad11` after the candidate-specific
final-head smoke test passed. FCR-044 is manually verified, FCR-002 navigation
verification is re-closed, and V-01 is satisfied by the exact SHA. FCR-042 and
FCR-043 remain non-blocking Product Hardening backlog.

This closure changes governance documentation only. It does not modify product
behavior, models, revisions, thresholds, privacy contracts, workflows, or the
tested behavioral candidate. Release readiness remains No; the next lifecycle
phase is Product Hardening.

## Review ergonomics — Windows one-click launcher

Added `start_social_text_intelligence.bat` at the repository root after explicit
user approval. The launcher resolves the project `.venv` with relative paths,
starts the existing loopback-only web app in offline mode, opens the browser,
and provides setup and shutdown guidance. It installs and downloads nothing and
does not change application, model, privacy, or persistence behavior.

## Feature Complete Review — FCR-044 return navigation

Reclassified FCR-044 as a pre-freeze blocker after candidate-specific manual
review showed that four internal Support Triage views lacked a discoverable
return to the main application and caused material operating difficulty. Added
an explicit `Social Text Intelligence home` link to every non-root workflow
view, including deep Triage and Moderation pages, while preserving each
workflow's own subnavigation and all temporary state.

Reopened FCR-002 navigation verification and added route regressions covering
the four Triage internal views plus Moderation session/review pages. No workflow,
model, data, privacy, persistence, or decision semantics changed.

## Feature Complete Review — pre-freeze blocker corrections

Classified the completed manual review into product findings, QA governance,
and release ergonomics. Recorded FCR-034 through FCR-044 without treating every
questionnaire suggestion as a product FCR. Established a tracked `manual-qa/`
home for the bilingual questionnaire, synthetic samples, and guidance, while
repository ignore rules keep raw results, screenshots, exports, and machine
paths out of Git.

Clarified emotion neutral threshold-fallback copy, added Batch filter anchoring
and destructive-clear confirmation, surfaced Human Review completion and
Context Note UTC timestamps, exposed reliable/unassigned Insight failure
counts, made Triage no-mock state explicit, and restored the linked
Batch-to-Triage entry. These changes preserve models, thresholds, labels,
privacy defaults, denominators, and process-memory boundaries. Feature Freeze
remains pending explicit approval after candidate-specific manual retest.

## Feature Complete Review — local model-cache hardening

Hardened the pinned Cardiff sentiment runtime so Transformers must load the
audited `pytorch_model.bin` artifact and cannot silently create a separate
Safetensors conversion-revision snapshot. Added a regression test for the
immutable revision, offline option, remote-code boundary, restricted weight
loading, and explicit artifact choice.

Repaired the machine-local Hugging Face cache after Windows Developer Mode was
enabled: the duplicate GoEmotions snapshot weight is now a symbolic link to its
content-addressed blob, and the unused Cardiff auto-conversion revision was
removed after real offline inference passed for both providers. Cache repair is
local-only and does not change a model, approved revision, label, score, product
contract, or tracked model artifact.

## Lifecycle alignment after Milestone 10

Created `ROADMAP.md` as the canonical mutable roadmap and
`PROJECT_STATUS.md` as the canonical current-state record. Added the bilingual
Feature Complete Manual Audit and the living manual-QA artifact, then aligned
the README, Charter, and development guidance around the post-M10 lifecycle.

The current phase is Feature Complete Review. Feature Freeze, Product
Hardening, full regression and manual acceptance, and Release Candidate
approval have not started or passed. Former M11–M12 remain deferred
next-version candidates; former M13 is lifecycle evaluation, hardening,
acceptance, portfolio, and delivery work rather than another future feature.

## Milestone 10 — Local Support Triage workbench

Added a separate three-area Support Triage workflow over a versioned,
project-authored synthetic routing guide and 22 stable synthetic tickets.
Successfully parsed batch records are eligible through explicit snapshots even
when NLP inference failed; optional sentiment, emotion, human review, context
notes, and trusted metadata remain supporting context and never determine
routing automatically.

Added typed intents, categories, urgency, recommended queues, escalation
reasons, recommended actions, draft/finalized states, guide provenance,
deterministic mock provenance, structural validation, and non-blocking warning
contracts. Drafts may be incomplete but legal. Finalization is atomic and
freezes an immutable first decision; explicit revisions update a separate
current final decision.

Added Independent and deterministic mock-assisted simulation modes without a
real classifier or LLM. Human forms are never prefilled. First/final field-level
agreement and overrides remain descriptive and are never labeled accuracy,
quality, causal impact, or operator performance.

Added sample-aware summaries, overlapping follow-up reasons, filters, sorting,
and auditable formula-safe CSV export. Workspace-derived source text, NLP
signals, human review, context notes, and trusted metadata are blank by default
and require separate explicit opt-ins. Triage workspaces are process-memory
only, expire after inactivity, and block limits without silent eviction.

Planned feature milestones are now complete, but the project is not
feature-frozen or release-ready. Former Milestones 11–12 are deferred
next-version candidates. Former Milestone 13 is lifecycle work covering
evaluation, hardening, acceptance, portfolio, and delivery.

## Milestone 9 — Moderation training workflow

Added a versioned, project-authored synthetic moderation policy and a 20-case
synthetic training library with stable IDs, policy-clause provenance, complete
reference decisions, acceptable alternatives, sensitive-content markers, and
an explicitly labeled fixture mock provider. The mock provider executes no
model and is never presented as expert judgment or accuracy ground truth.

Added typed moderation contracts and separate structural validation versus
non-blocking policy guidance. Structural errors reject incomplete or conflicting
decisions. Guidance warnings preserve unusual but contextually possible
combinations without rewriting or blocking the user's judgment, and remain in
feedback, comparisons, and export. References distinguish `built_in` from
`self_authored`; the reserved `user_authored` provenance is not exposed as a
current single-user authoring choice.

Added explicit successful-record snapshot preparation, frozen policy/reference
sessions, independent and synthetic-mock-assisted modes, immediate or
end-of-session feedback, immutable first decisions, explicit final revisions,
cancel/restart history, field-level comparison, educational flags, sample-aware
raw summaries, and auditable formula-safe CSV export with privacy-default
exclusions.

Added a three-area Prepare, Train, and Review interface plus configurable
process-memory limits of 100 prepared cases, 50 cases per session, and 20
retained attempts. Limits block new objects without silently deleting existing
work. This milestone adds no live moderation model, automatic enforcement,
support triage, LLM, persistence, platform connector, account, French support,
or new dependency.

## Milestone 8 — Insights and community context

Added reusable trusted-group validation, separate AI/human/agreement
perspectives, exact metric-specific denominators, review-coverage measures, and
per-group sample-size policy. AI activation remains threshold-based and
multi-label; definitive human and disagreement metrics exclude partial and
uncertain dimensions without silently changing the denominator.

Added Group Explorer, two-to-four-group Distribution Comparison, AI vs Human,
Representative Cases, Phrase and Context Notes, and explicit Insight Export to
the existing local Flask workspace. Examples are selected by declared
deterministic rules. Context notes are user-authored, validated, and stored
separately from immutable AI results and human reviews.

Insight summaries retain model and review provenance, disclosures, filters, raw
counts, denominators, and sample warnings. Optional record-level and native-score
export remains off by default, and formula-like user-controlled cells are
escaped. A narrow conformance patch made exports self-auditing with UTC export
and context-note timestamps, metric definitions, configured sample thresholds,
complete input/analysis/review counts, and explicit successful, failed, and
unassigned failed-row group context. Failed rows are grouped only from reliably
validated supported metadata and never by inference. This milestone adds no
model, dependency, LLM narrative, inferred identity, ranking, causality,
automation, persistence, account, cloud service, platform connector, French
support, or moderation workflow.

## Milestone 7 — Human-in-the-loop review

Added a focused review queue for successful batch outcomes. Sentiment and
multi-label emotion use separate accept, correct, and uncertain judgments;
partial work remains unreviewed until both dimensions are decided. Corrected
emotion labels enforce compact-taxonomy membership, uniqueness, dominant versus
secondary separation, stable ordering, and neutral exclusivity. Human fields are
replaced immutably without rewriting the original AI report or provenance.

Added review-state and AI-label filters, safe queue navigation, per-record Accept
Both, optional notes, honest model-human agreement summaries, sentiment confusion,
emotion set comparisons, and bounded confidence-band descriptions. Agreement
denominators exclude whole-record partial reviews, failures, and the uncertain
dimension. No result is described as model accuracy or calibrated confidence.

Added explicit reviewed CSV export with separate human fields, agreement values,
UTC timestamps, failures, AI results, model revisions, and optional native scores.
Spreadsheet formula protection covers review notes and existing user-controlled
cells. Reviews share the bounded, expiring in-memory batch workspace and add no
database, autosave, re-import, training, accounts, cloud service, or Milestone 8
analytics.

## Milestone 6 — Batch input and export

Added an explicit CSV upload, column-selection, preview, and validation workflow.
Supported normalized metadata is trusted only by name; unknown columns are
reported and ignored. Missing IDs receive deterministic row identities, while
duplicate supplied IDs and invalid rows remain visible typed outcomes.

Added resilient sequential batch analysis using the same lazily reused providers,
one outcome per input row, filters, semantically distinct aggregate views, and
explicit normalized CSV export with optional native emotion scores. CSV cells
that could trigger spreadsheet formulas are safely escaped.

Uploads and results use a bounded, expiring in-memory workspace and no durable
storage. This milestone adds no database, automatic export, history, accounts,
French model support, platform connector, or hosted deployment.

## Milestone 5 — Local analysis interface

Added an original local Flask interface for direct English text analysis. The
page displays normalized sentiment and emotion results, optional native scores,
threshold and provenance details, operating mode, first-load guidance, and
plain-language limitations.

Added a thread-safe lazy analysis-service container so both model providers are
constructed once and reused across requests. Expected validation, language,
cache, dependency, and provider failures become safe user-facing messages. The
server binds to loopback and does not log or persist submitted text.

This milestone adds no batch input, history, persistence, accounts, French,
platform connectors, hosted deployment, or separate frontend application.

## Milestone 4 — Licensed fine-grained emotion analysis

Audited English social-text emotion models for license clarity, provenance,
base model, immutable revision, native labels, multi-label support, neutral
semantics, loading format, and technical fit. Approved the MIT-licensed Sam Lowe
GoEmotions model and its Safetensors artifact; documented rejected candidates.

Added local multi-label inference, preservation of all 28 native probabilities,
conservative compact taxonomy mapping, explicit inclusive threshold semantics,
dominant and ordered secondary emotions, neutral fallback, typed validation, and
a single-text combined sentiment/emotion report. Added deterministic tests and
an opt-in real-model combined smoke test.

This milestone adds no UI, batch input, persistence, French capability, platform
connector, remote inference, real user text, dataset, or model weights.

## Milestone 3 — Licensed local sentiment analysis

Audited locally executable sentiment models for license clarity, provenance,
native-label compatibility, loading safety, language, and technical fit. Approved
the Cardiff NLP Twitter-roBERTa sentiment model at an immutable revision and
documented rejected candidates.

Added lazy local inference, model-specific social-text preprocessing, one-to-one
negative/neutral/positive mapping, normalized native and application scores,
single-text service and CLI workflows, explicit unsupported-language and invalid
output handling, deterministic provider tests, and an opt-in real-model smoke
test. Updated licensing, setup, architecture, limitations, and privacy guidance.

This milestone does not add emotion inference, batch input, persistence, a user
interface, remote inference, telemetry, real user text, or model weights.

## Milestone 2 — Text analysis core contracts

Added the model-independent analysis core:

- normalized, immutable text records with explicit metadata validation;
- compact sentiment and emotion taxonomies from the Project Charter;
- separate normalized and model-native score contracts;
- provider identity, model revision, supported-language, and native-label metadata;
- stable sentiment and emotion provider protocols;
- deterministic mock providers for fast, offline tests;
- provider-neutral analysis orchestration and typed error contracts.

The mock providers do not interpret text and are not real NLP models. Milestone 2
adds no model weights, runtime dependency, persistence, UI, network access, or
user data.

## Milestone 1 — Independent local project foundation

Established the project's independent, privacy-first development baseline:

- adopted the Project Charter as the stable product reference;
- added safe Git exclusions and cross-platform text conventions;
- created a minimal dependency-free Python package and diagnostic command;
- added deterministic unit tests and continuous integration;
- documented architecture, privacy, security, development, and model governance;
- clarified that source-code licensing does not relicense models or datasets.

No NLP model, text analysis contract, user interface, persistence layer, user
data, or platform adapter is included in this milestone.
