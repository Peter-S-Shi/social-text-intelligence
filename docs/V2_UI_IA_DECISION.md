# V2 UI/IA Decision Record

Status: **UI/IA Gate: PASS (2026-10-07, repository-owner decisions in section
2).** Baseline: `main` at `c17e07c` (V2 Application Foundation merged, PR #38).
This is a governance record. It changes no product code, test behavior,
dependency, or version, and it does not copy any prototype material into `main`.

Related records: [V2 Product Discovery](V2_PRODUCT_DISCOVERY.md) (Product Scope
Gate) and [V2 Desktop Architecture Exploration](V2_DESKTOP_ARCHITECTURE_EXPLORATION.md)
(Architecture Gate). Live phase state is recorded only in
[Project Status](../PROJECT_STATUS.md).

## 1. Evidence reviewed

The UI/IA exploration was a throwaway sidecar kept on branch
`prototype/v2-ui-ia-exploration` (head `9543c9e`), out of `main`. It was not
merged and is not copied here. The gate considered its round 3 material, which
lives only on that branch under `prototypes/v2-ui-ia/round3/`:

| Artifact | What it contains |
| --- | --- |
| `UI_IA_GATE_R3.md` | The round 3 brief: IA, screen list with feature coverage, and the two owner questions |
| `FEATURE_BOUNDARY.md` | An inventory of the V1 surface as feature IDs (F1–F6.5) derived from the V1 code, plus four gate-approved V2 additions (V2-1 to V2-4) |
| `REFERENCES.md` | A curated reference set used for structure and typography only |
| `sti-v2-r3-samples.html` and `shots/` | An interactive product demo and route screenshots |

Properties of that evidence that bound how far it can be relied on:

- The demo is synthetic. Model output in it is a scripted stand-in and nothing
  is written to disk. It shows no real model quality or performance.
- Its brief states that **accessibility and LGPL compliance were not assessed**.
  The architecture record's pre-distribution LGPL gate and an accessibility audit
  remain open.
- It loads web fonts for the mock only. The brief says the three typefaces are
  OFL-licensed and can be bundled; that licence claim was not independently
  verified here and must be checked before any font is shipped, with an entry in
  [Third-Party Notices](../THIRD_PARTY_NOTICES.md). A shipped V2 build must not
  fetch fonts from the network.
- Earlier rounds (variants A to F) exist on the same branch and were not
  re-read for this record; round 3 supersedes them.

## 2. Decisions

| ID | Decision | Binding content |
| --- | --- | --- |
| U1 | **Round 3 is the approved V2 UI/IA baseline** | Future implementation may polish the visual treatment (palette, typography, spacing, iconography). Three things are **fixed**: the project-centred information architecture; the strict feature boundary of V1 plus gate-approved additions; and the visual and semantic separation of the immutable AI record from the human judgment |
| U2 | **V2-4 means batch progress plus cancellation, with the M3 atomic no-partial-commit behavior preserved** | A cancelled analysis commits nothing and leaves the workspace as it was. The prototype's "finished rows survive cancellation and can resume later" behavior is **not approved**; it may be reconsidered only in a future persistence/job milestone |
| U3 | **Model provisioning (V2-2) requires progress, recovery, and offline/pre-provisioned support** | Pause and resume remain an implementation candidate, not a binding contract |
| U4 | **Moderation Training and Support Triage: P2 — retired from the V2 product surface** | V1 `0.10.0` and the repository history preserve them. They do not appear in the V2 desktop product |

### U1 — what is fixed and what is not

**Fixed (changes need a new gate decision):**

- **Project-centred IA.** The start window is the project list; one project is one
  imported CSV and everything derived from it. Its pages are import and
  validation, results, review, agreement, and the two insight views. A separate
  Tools area holds unsaved single-text analysis, as in V1. First run is a
  separate setup window, and model status is always visible in the sidebar.
- **Strict feature boundary.** Only V1 behavior (the feature IDs in the
  prototype's `FEATURE_BOUNDARY.md`) and the gate-approved V2 additions (below)
  may appear. The round 2 inventions it removed stay out: several CSV sources
  per project, adding Direct results to a project, margin-based "mixed signal"
  flags, probes and calibration, similarity or theme features, retention timers,
  encryption claims, accounts, sync, and sharing.
- **AI record versus human judgment.** On every review surface the machine record
  and the human judgment are separate, equally weighted, and visually and
  semantically distinct; the AI record is never edited, only judged.

**Not fixed (implementation may change):** colors, typefaces, spacing,
component styling, iconography, motion, and exact layout details, provided the
fixed items hold.

### U2 — the amended V2-4

| | Approved V2-4 | Not approved |
| --- | --- | --- |
| Progress | Visible row progress during batch analysis | — |
| Cancel | User cancellation that aborts the analysis | Keeping finished rows after cancellation |
| Atomicity | Cancellation or failure releases the analysis lease and commits no partial result, as in the M3 application layer (`BatchCancelled`, lease cancel) | Resuming a cancelled analysis later |

This replaces the prototype boundary's wording "keeps finished rows".

### U3 — model provisioning contract

Binding: download of the pinned revisions with visible progress; recovery after
interruption or failure; and an offline or pre-provisioned path (a user-supplied
models folder). Not binding: pause and resume, which may be adopted if
implementation shows they are cheap and safe.

### U4 — Moderation Training and Support Triage

- The V2 product surface has no Decision Practice area. The prototype's screens
  10 and 11 and their navigation entry are not part of the baseline.
- This resolves the open final disposition left by the Architecture Gate (A8):
  of its two options, explicit retirement is chosen, not a demoted native
  surface. It supersedes the Product Scope Gate's "keep, fold, and demote" for
  the V2 product surface.
- **No code is removed by this gate.** The V1 implementation remains in `main` and
  in history, and the frozen Flask compatibility surface continues to expose it
  while that surface exists. Whether and when to delete the code, tests, and
  documents from `main` is a later scoping decision and is not made here.
- Consequence for scope: no further investment, and no desktop home for these
  workflows.

## 3. Resulting V2 feature boundary

V2 = V1 behavior for direct analysis, batch CSV, human review, agreement,
insights, notes, representative cases, and exports, **minus** Moderation Training
and Support Triage, **plus** these gate-approved additions:

| ID | Addition | Status after this gate |
| --- | --- | --- |
| V2-1 | Persistent local project (one imported CSV and everything derived), kept until manually deleted; list, open, delete with conservative wording | Approved; implementation is the next mainline milestone |
| V2-2 | First-run model provisioning | Approved with the U3 contract |
| V2-3 | Language detection with an unsupported-language warning | Approved; milestone placement not yet scoped |
| V2-4 | Batch progress and cancellation | Approved as amended by U2; implemented at the application layer in M3, desktop presentation later |

## 4. What this gate does not decide

- The detailed scope and acceptance criteria of M4 (see section 5).
- The desktop shell implementation, packaging, accessibility audit, and the
  pre-distribution LGPL compliance review.
- The persistence schema details, WAL/sidecar cleanup, and job semantics beyond
  U2.
- Removal of Moderation and Triage code, tests, and documents from `main`.
- Any model quality claim; the representative-domain evaluation gate (Product
  Scope Q5) still applies.

## 5. Next mainline milestone

After this record merges, the next mainline milestone is
**M4 — V2 Persistent Project Foundation**. It has not started and is not scoped
here beyond its title. Binding inputs it inherits from earlier gates and this
one: one SQLite file per project under per-user LocalAppData; keep until
manually deleted with no automatic expiry; no encryption claim; conservative
deletion wording with WAL/sidecar cleanup; V2-1 as defined above; and the
framework-free application layer and `ProjectRepository` port established in
M3 (V2 Application Foundation). Its boundary and acceptance checks are to be
defined when the milestone starts.
