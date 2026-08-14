# Social Text Intelligence — Feature Complete Review Handoff

**Date:** 2026-08-13
**Purpose:** Convert the completed manual QA evidence into an engineering/governance handoff for Codex before the Feature Freeze gate.
**Repository:** `social-text-intelligence`
**Current product version:** `0.10.0`

> This file is a bridge artifact. It does **not** replace:
> - `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md` — canonical FCR decision record
> - `PROJECT_STATUS.md` — canonical current project state
> - `manual_review_questionnaire.html` and its exported JSON — raw/manual QA evidence
>
> Codex should use this handoff to update the canonical records, implement approved corrections, add/confirm targeted regression, and return the repository to the user for explicit Feature Freeze review.
> **Do not auto-pass Feature Freeze.**

---

## 1. Evidence baseline

### 1.1 Manual QA export

Raw manual QA evidence supplied by the reviewer:

- Project: `Social Text Intelligence`
- App version recorded by questionnaire: `0.10.0`
- Questionnaire version: `2.0`
- Schema version: `2.0`
- Review date field: `2026-08-11`
- The raw export, exact timestamp, fingerprint, reviewer-entered notes, and
  aggregate result counts remain local under `manual-qa/results/` and are not
  reproduced in tracked guidance.

Important evidence limitation:

- The exported questionnaire records `appRevision = 0.10.0`, not a Git commit SHA.
- Reviewer identity and machine environment are intentionally not copied into
  tracked guidance.
- Therefore this export is strong manual behavior evidence, but it must **not** be represented as commit-specific final acceptance.
- Before Feature Freeze / final regression, establish a known candidate SHA and rerun all affected checks plus the final required regression on that exact revision.

### 1.2 Repository state reviewed for this handoff

At review time, GitHub `main` HEAD is:

`dc70857ffef7e63997376b97510ab62389a20c41`

Commit message:

`Merge PR #15: Record PR 14 merge status`

That commit changes only `PROJECT_STATUS.md` and records the previously validated behavioral revision:

`d896c4791653e674919c57e643362d90ebbcf317`

Current canonical repository documents still state:

- Lifecycle phase: `Feature Complete Review`
- Feature Complete Review: not completed
- Feature Freeze: not started
- Product Hardening: not started
- Release readiness: no
- FCR-033: verified
- FCR-001–FCR-032: still largely open in the audit index

This is correct in spirit: the product has **not** yet passed the freeze gate.

---

## 2. Gate recommendation

### Feature Freeze recommendation at handoff creation

**DO NOT PASS YET**

Reason:

1. Several explicit manual-QA expectations failed.
2. One major linked Support Triage workflow is blocked by a missing normal-user entry path.
3. Several verification dependencies remain unresolved.
4. The canonical FCR audit has not yet absorbed the manual QA dispositions.
5. The manual QA export is not tied to an exact tested commit SHA.

### What is already strong

The manual review provides broad, high-confidence evidence across:

- local/offline boundary and startup;
- direct sentiment/emotion surfaces;
- Batch parsing, partial failure, filtering and exports;
- Human Review decisions, summary and formula-safety sample;
- Insights grouping, denominators, perspectives and export;
- Moderation Training lifecycle, warnings, feedback and privacy export;
- most Support Triage lifecycle/summary behavior;
- keyboard accessibility;
- narrow-layout responsiveness;
- English-only boundary;
- console privacy;
- `Cache-Control: no-store`;
- process-memory expiry/clear/restart semantics;
- safe invalid/expired-token recovery.

The remaining work is **concentrated**, not a broad product failure.

---

## 3. Raw QA findings requiring disposition

The following observations in the exported QA record must not be lost when the canonical audit is updated.

| QA item | Raw status | Finding / dependency | Recommended treatment |
|---|---:|---|---|
| `direct-multilabel` | N/A | Independent emotion scores and threshold fallback were observed, but no non-empty secondary-emotion case was exercised. UI may confuse `dominant=neutral` with highest raw neutral score when neutral is actually a threshold fallback. | Clarify fallback semantics; add/locate deterministic coverage for non-empty secondary emotion; retest. |
| `batch-filters` | Pass | Applying filters refreshes back to page top although the Results controls are near the bottom. | Non-blocking UX hardening; preserve/return to results anchor if low-risk. |
| `batch-clear` | **Fail** | Temporary batch is cleared immediately with no warning/confirmation; token invalidation itself works. | Current-version hardening. Add explicit destructive/temporary-state warning or confirmation semantics and retest. |
| `review-queue` | Pass | When all 20 reviews are complete there is no clear completion affordance; user only discovers completion because Next no longer advances. | Non-blocking workflow-completion hardening. |
| `insights-notes` | N/A | Context Note behavior works, but `created_at` / UTC semantics should be more directly visible in the Current context notes UI. | Non-blocking auditability hardening; retest exact expected semantics. |
| `insights-failures` | **Fail** | Edge group shows eligible/total correctly, so failed rows are not silently dropped, but successful / failed / reliably-unassigned failed counts are not explicitly separated in the UI. | Current-version hardening; expose the already-available separate counts without guessing group assignment. |
| `moderation-workspace` | Pass with explicit pending sub-check | Literal excerpt and self-authored provenance passed. Reviewer intentionally deferred verifying that failed Batch rows cannot be selected/prepared, including request-level bypass. | Static/service/test verification required; do not change behavior unless a gap is found. |
| `triage-mock-source` | **Fail** | Filtering works and no mock is fabricated, but no-mock state is not explicitly shown as unavailable. | Same root cause as `triage-visibility`; one fix/FCR should cover both. |
| `triage-visibility` | **Fail** | Assisted no-mock ticket shows generic copy claiming “the visible suggestion is a deterministic synthetic mock” even though no suggestion exists. Human form remains unprefilled. | Current-version hardening: explicit unavailable state + conditional assisted copy. |
| `triage-workspace` | N/A / blocked | Batch Results has `Prepare Moderation Training` but no equivalent `Prepare Support Triage` preserving the active batch token. Normal user cannot enter the intended linked Triage workflow. | Current-version hardening; restore the already-supported linked-workspace workflow through a normal UI entry point. |
| `triage-export` | Raw JSON says Pass | During manual review, only built-in-synthetic export Phase A was actually confirmed. Workspace-derived privacy-default + five independent opt-ins could not be fully retested because linked Triage workspace creation was blocked. | Treat FCR-024 as **not fully verified** until linked Triage is restored and workspace-derived export is retested. Do not edit the raw JSON; record this reconciliation in the FCR audit. |

---

## 4. Proposed new FCR records

The current audit maintenance rule says each independently decidable new finding receives the next permanent `FCR-XXX` ID. Current maximum is FCR-033. Create the following records unless repository inspection shows an equivalent existing FCR was added after this handoff.

### FCR-034 — Emotion neutral threshold-fallback semantics

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** Pre-freeze correction recommended because transparent score/threshold semantics are a core product contract.
- **Evidence:** `direct-multilabel`
- **Problem:** When no non-neutral compact emotion reaches threshold, UI can show `dominant=neutral` although raw neutral score is lower than another raw emotion score. Current UI does not explicitly say this is a threshold fallback.
- **In scope:** Clarify fallback semantics in UI/copy without changing model, scores, threshold, labels, or compact/native contracts.
- **Out of scope:** New model, threshold tuning, semantic reinterpretation, multilingual work.
- **Acceptance:** A user can tell that `neutral` is a fallback state rather than “the highest emotion score.” Existing threshold and independent-score semantics remain unchanged.
- **Retest:** `direct-multilabel` plus a deterministic/known case that produces non-empty secondary emotion if available.

### FCR-035 — Batch filter result-position usability

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** Non-blocking; suitable for post-freeze Product Hardening unless bundled safely with related UI work.
- **Evidence:** `batch-filters`
- **Problem:** Applying filters returns the browser to the top although filter/results controls are low on the page.
- **Acceptance:** Applying/restoring filters does not force unnecessary manual scrolling back to Results; no filter/data semantics change.

### FCR-036 — Temporary Batch clear warning/confirmation

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** **Current-version blocker** because the explicit QA contract failed on a destructive temporary-state action.
- **Evidence:** `batch-clear`
- **Problem:** `Clear this temporary batch` immediately destroys process-memory batch state with no warning/confirmation semantics.
- **Acceptance:** Clear remains explicit and local/temporary; user receives an understandable warning/confirmation before destruction; after confirmation the old token is invalid; unrelated workspaces remain unaffected.

### FCR-037 — Human Review completion affordance

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** Non-blocking; Product Hardening candidate.
- **Evidence:** `review-queue`
- **Problem:** After the final review, workflow completion is not clearly surfaced.
- **Acceptance:** Completion state is explicit without altering saved human decisions, denominators, or navigation semantics.

### FCR-038 — Context Note UTC timestamp visibility

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** Non-blocking unless static inspection shows the required UTC created-at semantics are actually absent.
- **Evidence:** `insights-notes`
- **Problem:** Current note card does not make creation time/timezone sufficiently direct for the reviewer.
- **Acceptance:** Saved note visibly exposes created-at semantics with UTC unambiguous; no note/prediction/review semantics change.

### FCR-039 — Insights explicit failed/unassigned group counts

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** **Current-version blocker** because the explicit QA contract failed and this affects descriptive denominator transparency.
- **Evidence:** `insights-failures`
- **Problem:** Edge group does not silently discard failures, but UI requires users to infer failures from eligible vs total instead of explicitly showing successful / failed / reliably-unassigned counts.
- **Acceptance:** Group context displays separate successful, failed, and reliably unassigned-failed counts using existing trustworthy backend summary data; no guessed grouping; existing denominators remain unchanged.

### FCR-040 — Support Triage explicit no-mock state

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** **Current-version blocker** because two explicit QA checks failed and current Assisted copy is misleading.
- **Evidence:** `triage-mock-source`, `triage-visibility`
- **Problem:** No mock is fabricated, but the unavailable state is not explicit; Assisted generic copy can claim a visible deterministic mock when none exists.
- **Acceptance:**
  - no-mock ticket explicitly says `Mock unavailable` or equivalent;
  - no suggestion is fabricated;
  - Assisted notice is conditional on actual mock availability;
  - human form remains unprefilled;
  - Independent/Assisted available-mock visibility behavior and counts do not regress.

### FCR-041 — Linked Support Triage entry from Batch Results

- **Decision Class:** `HARDENING`
- **Recommended Decision:** `Keep and harden`
- **Status:** `OPEN`
- **Freeze impact:** **Current-version blocker** because an intended major workflow cannot be reached through the normal UI and blocks downstream manual verification.
- **Evidence:** `triage-workspace`; manual inspection of Batch Results
- **Problem:** Batch Results exposes `Prepare Moderation Training` with active batch context but only generic Support Triage navigation; the Triage home already supports a temporary batch token, yet normal users cannot carry the active token into a linked Triage workspace.
- **In scope:** Add/restore a normal Batch Results entry point that preserves/passes the active temporary batch token into Support Triage.
- **Out of scope:** Persistence, new ticket source types, new top-level workflow, connector work.
- **Acceptance:**
  - main 20-row batch can create a linked Triage workspace through the UI;
  - edge batch can create a linked Triage workspace through the UI;
  - successful parsed records can be snapshotted;
  - `edge-fr-001` remains triage-eligible despite provider analysis failure;
  - NLP/review/notes/metadata remain supporting context only;
  - expired/cleared tokens retain safe recovery behavior.

---

## 5. FCR-001–FCR-033 disposition map

This table is a **review recommendation**, not a substitute for appending the canonical audit records.

| FCR | Recommended state after evidence review | QA / evidence basis | Required action before canonical closure |
|---|---|---|---|
| FCR-001 Startup & local boundary | `VERIFIED / Keep as-is` | setup launch/CLI/boundary/first-load; cross-cutting privacy/expiry | Record version-limited evidence; final clean-install belongs to RC. |
| FCR-002 Top navigation | `VERIFIED / Keep as-is` | `setup-nav` | None beyond canonical evidence entry. |
| FCR-003 Direct text input | `OPEN verification` | blank-input validation passed; Batch language boundary tested | Codex verify overlong and unsupported-language direct-input recovery through implementation/tests; add targeted test if coverage is missing. |
| FCR-004 Sentiment output | `VERIFIED / Keep as-is` | direct basic/mixed/provenance | Record evidence. |
| FCR-005 Emotion output | `OPEN — FCR-034 + verification` | native scores passed; `direct-multilabel` N/A with fallback ambiguity | Resolve FCR-034 and verify a non-empty secondary-emotion case. |
| FCR-006 Model limitations | `VERIFIED / Keep as-is` | setup boundary, mixed/sarcasm, English-only cross-check | Record evidence. |
| FCR-007 Batch preview | `VERIFIED / Keep as-is` | main/alternate/edge preview | Record evidence. |
| FCR-008 Batch partial failure | `VERIFIED / Keep as-is` | main + edge analysis; French provider failure preserved | Record evidence. |
| FCR-009 Batch filters & export | `VERIFIED with non-blocking FCR-035` | filters/export pass | Keep semantics; optionally harden result-position UX. |
| FCR-010 Human Review queue | `VERIFIED with non-blocking FCR-037` | queue pass | Keep queue semantics; harden completion affordance. |
| FCR-011 Independent human judgment | `VERIFIED / Keep as-is` | accept/correct/uncertain/navigation all pass | Record evidence. |
| FCR-012 Review summary/export | `VERIFIED / Keep as-is` | summary/export/formula sample pass | Record evidence; FCR-026 still needs global formula-safety scope verification. |
| FCR-013 Insights grouping | `VERIFIED / Keep as-is` | thresholds/comparison and trusted grouping behavior | Record evidence. |
| FCR-014 Insights metrics | `OPEN — FCR-039` | denominators/perspectives pass; failure-count UI fails | Fix/retest FCR-039. |
| FCR-015 Context Notes | `OPEN — FCR-038/retest` | note semantics mostly observed; timestamp UI marked N/A | Inspect whether contract is already technically satisfied; harden/retest as needed. |
| FCR-016 Insight export | `VERIFIED / Keep as-is` | auditable export pass | Record evidence. |
| FCR-017 Moderation source | `OPEN verification` | policy/filter/workspace mostly pass | Complete failed-row selection/request-bypass invariant verification. |
| FCR-018 Moderation decisions | `VERIFIED / Keep as-is` | structural + guidance-warning tests pass | Record evidence. |
| FCR-019 Moderation session | `VERIFIED / Keep as-is` | session/feedback/summary pass | Record evidence. |
| FCR-020 Moderation privacy export | `VERIFIED / Keep as-is` | privacy-default/all-opt-in behavior reviewed | Record evidence. |
| FCR-021 Triage source & draft | `OPEN — FCR-040` | source/draft pass; no-mock explicitness fails | Fix/retest FCR-040. |
| FCR-022 Triage finalize/revision | `VERIFIED / Keep as-is` | draft/final/revision/warning lifecycle pass | Record evidence. |
| FCR-023 Triage mock & summary | `OPEN — FCR-040` | summary/counts pass; visibility contract fails | Fix/retest FCR-040; preserve denominator/count semantics. |
| FCR-024 Triage privacy export | `OPEN verification, blocked by FCR-041` | raw JSON says pass; manual-session reconciliation says only built-in Phase A fully checked | After FCR-041, create workspace-derived case and retest privacy-default plus five independent opt-ins. |
| FCR-025 Privacy & local state | `VERIFIED / Keep as-is` | console privacy, no-store, expiry/clear/restart pass | Record evidence. |
| FCR-026 Formula injection | `OPEN verification` | synthetic Human Review note safely escaped | Codex verify formula escaping is applied to **all user-controlled CSV fields / all export families**; add coverage if missing. |
| FCR-027 Keyboard/accessibility | `VERIFIED / Keep as-is` | `cross-keyboard` pass | Record evidence. |
| FCR-028 Responsive layout | `VERIFIED / Keep as-is` | `cross-responsive` pass | Record evidence. |
| FCR-029 Errors & empty states | `VERIFIED / Keep as-is` | invalid/expired token recovery and bad-input paths pass | Keep separate from FCR-036 destructive-action confirmation. |
| FCR-030 Documentation consistency | `OPEN` | canonical docs predate current manual QA; `PROJECT_STATUS` still describes audit as pending | Synchronize audit/status after engineering dispositions; verify README/Charter/contracts/privacy statements against current behavior. |
| FCR-031 Current-version scope | `OPEN until dispositions recorded` | findings now identified/classified in this handoff | Append decisions to canonical audit; distinguish pre-freeze blockers from non-blocking Hardening; no new product domain. |
| FCR-032 Deferred scope | `VERIFIED / Defer as already recorded` | ROADMAP/PROJECT_STATUS keep French, long-form, connectors, persistence, etc. outside current version | Preserve boundary. |
| FCR-033 Model-cache redundancy | `VERIFIED` | existing canonical record | Do not reopen unless regression/evidence changes. |

---

## 6. Verification dependencies that are not independent product findings

Do **not** create a new product feature merely to close these. Use static inspection/tests plus targeted manual retest.

### V-01 — Exact tested SHA for final acceptance

Current QA export is versioned only as `0.10.0`, not a Git SHA.

Required:

- record the local/repository candidate SHA used for the final retest;
- ensure working tree/revision is known;
- run affected manual checks and final regression on that exact candidate;
- do not claim the current raw JSON alone is final commit-specific acceptance.

### V-02 — Non-empty secondary emotion

For `direct-multilabel`:

- identify a deterministic synthetic input already present in tests/fixtures, or add a safe synthetic QA fixture, that produces at least one non-neutral secondary emotion under the existing fixed threshold;
- do not tune the threshold/model merely to make the test pass;
- verify dominant/secondary/native/independent-score semantics.

### V-03 — Moderation failed-row preparation invariant

Reviewer explicitly deferred this sub-check.

Codex must verify from:

- UI selector construction;
- service/domain validation;
- direct/request-level bypass behavior;
- automated tests.

Required invariant:

> only successfully analyzed Batch records may be prepared into Moderation workspace cases.

If already enforced, document evidence and add missing regression only if needed. If not enforced, treat the discovered gap as a new FCR with the next permanent ID before implementation.

### V-04 — Triage workspace-derived privacy export

After FCR-041 restores linked Triage entry:

Use at least one workspace-derived ticket and test:

1. privacy-default export, none checked;
2. source text only;
3. signals only;
4. human review only;
5. context notes only;
6. trusted metadata only.

Expected:

- workspace source text/signals/review/context/metadata are blank by default;
- each category is released only by its own opt-in;
- built-in synthetic text may remain default-visible;
- UTC, guide, lifecycle, warnings, denominators and audit fields remain;
- no checkbox silently opts in another category.

The current raw JSON `triage-export = pass` must not be used to skip this reconciliation retest.

### V-05 — Direct-input boundary completeness

FCR-003 initial audit scope mentions blank, overlong, English and unsupported-language feedback. Manual QA strongly covers blank and cross-module English-only behavior, but not every Direct-input boundary.

Static/test verification should confirm:

- overlong input rejection/recovery;
- unsupported-language direct-input behavior;
- prior result is never misrepresented as the failed submission’s result.

### V-06 — Global CSV formula safety

Manual QA proved the synthetic Human Review note is safely escaped.

Codex must verify the escaping helper/contract applies to every user-controlled CSV cell across:

- Batch;
- Human Review;
- Insights;
- Moderation;
- Triage.

Do not manually enumerate every possible malicious value if shared implementation + representative regression proves the invariant.

---

## 7. Pre-freeze blocker set

Unless static inspection proves the observed behavior is already corrected in a newer candidate, treat these as the current **pre-freeze blocker set**:

1. **FCR-034** — emotion threshold-fallback meaning is not explicit enough for transparent interpretation.
2. **FCR-036** — Batch clear lacks warning/confirmation semantics.
3. **FCR-039** — Insights does not explicitly separate successful / failed / unassigned-failed counts.
4. **FCR-040** — Support Triage no-mock state/copy is misleading.
5. **FCR-041** — Batch Results lacks normal linked Support Triage entry, blocking a major workflow.
6. **V-03** — Moderation failed-row preparation invariant is not yet fully verified.
7. **V-04** — Triage workspace-derived privacy export is not yet fully verified.
8. **V-01** — final acceptance must be tied to a known candidate SHA.

FCR-035, FCR-037 and FCR-038 are recommended non-blocking Hardening items unless repository inspection elevates their impact.

---

## 8. Codex execution contract

### 8.1 First action: evidence and classification, not feature development

Read together:

- this handoff;
- the raw exported manual QA JSON;
- `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`;
- `PROJECT_STATUS.md`;
- `ROADMAP.md`;
- relevant contracts/tests/code for each finding.

Do not reinterpret a failed QA item as “new feature request” merely because a UI affordance is missing. The listed corrections restore existing current-version contracts/workflows.

### 8.2 Update the canonical audit before or with implementation

- Add FCR-034–FCR-041 as permanent records.
- Preserve FCR-001–FCR-033 history.
- Update the Feature decision index.
- Record each Decision Class, Decision, status, acceptance, regression scope and evidence.
- If inspection discovers a genuinely different independent problem, allocate the next permanent FCR ID.
- Do not duplicate the same root cause into multiple FCRs.

### 8.3 Implement the pre-freeze correction batch

Prioritize the blocker set. Keep changes narrow:

- no new language;
- no model/revision change;
- no connectors;
- no accounts/auth;
- no persistence;
- no new top-level workflow;
- no silent privacy-default changes;
- no changes to immutable historical human decisions.

The `Prepare Support Triage` correction is a missing entry into an already-supported linked workflow, not a new product domain.

### 8.4 Regression and retest

For each correction:

- add/use a targeted failing regression;
- run affected tests;
- run full automated quality suite before gate review;
- provide concise human retest instructions keyed to the original QA IDs.

Minimum manual retest set after the correction batch:

- `direct-multilabel`
- `batch-clear`
- `insights-failures`
- `triage-mock-source`
- `triage-visibility`
- `triage-workspace`
- `triage-export` workspace-derived Phase B
- any item affected by shared templates/helpers.

Also close V-03, V-05 and V-06 by static/test evidence.

### 8.5 Synchronize project state

After implementation/retest evidence exists:

Update at minimum:

- `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`
- `PROJECT_STATUS.md`
- automated/manual QA evidence references
- any behavior contract/document whose wording changed

`PROJECT_STATUS.md` must no longer say “No release blocker classified yet; manual audit pending” once findings are classified.

Repository-state note:

- GitHub `main` HEAD observed for this handoff: `dc70857ffef7e63997376b97510ab62389a20c41`
- behavioral revision recorded inside current status: `d896c4791653e674919c57e643362d90ebbcf317`
- `dc70857` is documentation-only (PR #15 records PR #14 merge state).
- For the next lifecycle update, distinguish the **behavioral tested SHA** from the **current repository HEAD** clearly.

### 8.6 Do not auto-pass the next gates

When corrections and verification are complete, report:

- current candidate SHA;
- FCR dispositions;
- remaining blockers;
- targeted test results;
- full-suite results;
- exact manual retests still required;
- recommended Feature Freeze decision.

Then stop for user review.

Feature Freeze must use the canonical explicit format:

```text
Feature Freeze decision:
Decision date:
Reviewed version and SHA:
Decision: PASS / DO NOT PASS
Open current-version blockers:
Approved exceptions:
Required regression:
Approver:
Evidence:
```

Do **not** record `PASS` without explicit user approval after the evidence is reviewed.

---

## 9. Session 08 status at handoff creation

### 08.01 — Major workflows exercised with version-specific evidence

**DO NOT PASS YET**

Most workflows were exercised, but:

- linked Support Triage is blocked;
- workspace-derived Triage privacy export needs reconciliation retest;
- Moderation failed-row preparation invariant is pending;
- final QA is not tied to an exact commit SHA.

### 08.02 — Every finding has FCR ID, class and status

**DO NOT PASS YET**

This handoff proposes the mapping and FCR-034–FCR-041. The canonical audit must still be updated and dispositions accepted/recorded.

### 08.03 — Deferred next-version scope remains isolated

**PASS**

Current roadmap/status continue to defer:

- French/multilingual;
- transcript/long-form;
- connectors;
- persistence;
- accounts/shared/cloud;
- other new models/input domains/top-level workflows.

The corrections in this handoff do not require reopening those product domains.

### 08.04 — Explicit Feature Freeze decision recorded

**NOT EXECUTED**

Correct current state. Do not execute until 08.01 and 08.02 are closed and there are no unresolved current-version blockers.

---

## 10. Definition of done for this handoff

This handoff is complete when Codex can return a concise report showing:

- FCR-034–FCR-041 recorded with stable IDs;
- blocker/non-blocker dispositions recorded;
- approved blocker corrections implemented;
- V-01–V-06 resolved by appropriate manual/static/test evidence;
- affected manual QA retests completed or clearly handed back to the reviewer;
- full automated regression passed on a known candidate SHA;
- `PROJECT_STATUS.md` and audit state synchronized;
- no accidental scope expansion;
- a Feature Freeze decision is **ready for explicit user approval**, not automatically passed.

---

## 11. Source-of-truth precedence

If there is disagreement between artifacts:

1. **Raw exported QA JSON** preserves what the reviewer recorded at export time; never rewrite it.
2. **This handoff** records the post-session reconciliation and engineering interpretation, including the `triage-export` limitation that the raw JSON does not capture.
3. **`FEATURE_COMPLETE_MANUAL_AUDIT.md`** becomes the canonical long-term decision record once updated.
4. **`PROJECT_STATUS.md`** becomes the canonical current-state summary once updated.
5. **ROADMAP / Charter / contracts** define lifecycle and stable scope boundaries, not evidence that a test actually passed.

Where evidence is uncertain, preserve it as `OPEN verification`; do not convert uncertainty into a pass.
