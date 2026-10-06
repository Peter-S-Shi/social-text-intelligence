# V2 UI/IA exploration: Human Gate brief

Sidecar exploration, run in parallel with V2 Application Foundation. It changes
no production code, no lifecycle state, and no dependency. Everything here is a
throwaway PySide6 prototype on branch `prototype/v2-ui-ia-exploration` with
synthetic data. Screens: [screenshots/](screenshots/). Run: [README](README.md).

## 1. Fixed inputs (not reopened)

The V2 thesis (private, local review workbench for text evidence), Windows-first
PySide6 Qt Widgets, one persistent local project per SQLite file, Human Review
as the product centre, an immutable AI record kept separate from human
judgment, Direct, Batch, Review and Insights as one evidence workflow, no new
Moderation/Triage investment, no Flask dependency, the English-only
language warning, conservative delete wording, and no encryption claim.

## 2. V1 UI inspected

V1 is four top-level web tabs: Direct analysis, Batch CSV, Moderation
Training, Support Triage. Review and Insights exist only inside a Batch
workspace. Batch is a numbered three-step page (upload, preview and validate,
results). Review is a per-record form with Accept, Correct and Uncertain for
each dimension, plus an "Agreement, not accuracy" summary. Insights is a
filter-heavy page: views, metric and denominator, groups, representative
cases, and context notes. All state is expiring process memory.

## 3. Three directions

| | A. Evidence Workbench | B. Guided Pipeline | C. Review Desk + Report |
| --- | --- | --- | --- |
| Metaphor | IDE or mail client | Wizard with a stage rail | Annotation desk plus written report |
| Frame | Menu bar, navigator dock, record table, inspector dock, jobs dock, status bar | Project cards; inside a project, a five-stage rail and one stage at a time | Slim dark rail; desk, focus review, report, data |
| Review | Select any row; the inspector shows the AI record next to your judgment | Stage 3: list on the left, "what the models said" vs "what you decide" | One record full-width, serif quote, keyboard choices (1/2/3, Q to Y, A, U, Enter) |
| Direct analysis | Quick analysis dialog (Ctrl+Shift+A); "Add as record" or discard | "Try one text" sandbox on Home, outside projects | Ctrl+K palette; "Add to this project" |
| Batch | Import as a source tab; streaming rows; jobs dock with pause and cancel | Stages 1 and 2: mapping and validation, then a big progress view | Data page with an import drawer |
| Insights | Document tab: metric strip, group table with small-sample flags, confusion grid | Stage 4: three big numbers and per-channel bars | Paginated written report: big serif numbers, findings, representative cases, method |
| Best at | Density, mixed work, long sessions, native feel | First use, legibility, explaining the method to a reviewer | Review throughput and reading results as evidence |
| Weak at | First-run learnability; risks "Qt dashboard" clutter if undisciplined | Repeated work; going back and forth between stages; feels like a web wizard | Browsing or sorting many records; tables and filters are secondary |
| Qt fit | Very high (`QMainWindow`, docks, tables, actions, shortcuts) | High, but custom-painted rail and cards | Medium (custom chips, serif report pages, palette overlay) |

Screens:

- A: `a_launcher`, `a_review`, `a_batch`, `a_insights`, `a_quick`
- B: `b_home`, `b_import`, `b_analyze`, `b_review`, `b_insights`
- C: `c_desk`, `c_review`, `c_report`, `c_data`, `c_palette`
- Shared: `s_welcome`, `s_download`, `s_download_error`, `s_states`,
  `s_practice_keep`, `s_practice_retire`

## 4. Cross-cutting proposals (direction-independent)

- **Project lifecycle.** Start window (recent projects, new, open, quick
  analysis) → project → close. A project is a file under
  `%LOCALAPPDATA%\SocialTextIntelligence\projects`. Saving happens
  automatically per judgment and per analyzed row, so there is no Save button.
  Delete uses the conservative wording ("removed from this application's data
  files ... not a secure erase") and offers "Export first".
- **First run and models.** A welcome dialog states the only network request,
  then offers three paths:
  - download now (pinned revisions, verified after download);
  - use a pre-provisioned folder (offline path, rejects a revision mismatch);
  - later (projects and import work; analysis is disabled).

  Downloads are resumable and pausable, and a partial file is never used. The
  sentiment model can be ready while the emotion model is still missing.
- **States** (shown on `s_states`):
  - empty project;
  - model warm-up, which keeps the window responsive;
  - cancel confirmation, which keeps finished rows and leaves the rest
    queued;
  - row-level failures, kept with their reason;
  - possible non-English rows, marked and excluded from insights by default;
  - delete;
  - project open in another window;
  - save failure (disk full);
  - analysis unavailable.
- **Honest headline.** No V2 surface shows a bare "dominant emotion" verdict.
  Mixed, low-margin and threshold-fallback results show as "Unsettled
  sentiment (leans positive)", "mixed emotion: joy / anger", or "no emotion
  above threshold". This fixes the V1 probe finding where the headline
  contradicted the text.
- **The AI record and human judgment are visually separate everywhere.** The
  AI record uses slate with a read-only label; your judgment uses green and is
  "saved separately". The AI's pick is shown next to your choice (C uses a
  dashed outline) and is never overwritten.
- **Visual hierarchy.**
  - Near-white neutral surfaces and V1's green as the only accent.
  - Amber for caution, red only for failures.
  - Monospace for provenance (model@revision, IDs, counts); large light
    numerals for the few metrics that matter.
  - No charts without a stated denominator.
  - Light theme only for V2.0; the colour tokens are already centralised if
    dark mode is added later.

## 5. V1 concepts: survive or disappear

| V1 concept | Verdict |
| --- | --- |
| Four peer top-level tabs | **Disappears**; replaced by a project-centred frame |
| Direct analysis as a top-level workflow | **Demoted** to Quick analysis (scratch, not saved unless added to a project) |
| Batch as a numbered 1-2-3 page | **Disappears** as a page; becomes import plus a background job per source |
| Preview and validation before analysis | **Survives** (valid, invalid, possibly non-English counts; row-level reasons) |
| Row-level failure isolation | **Survives**; failed rows are kept and visible, never dropped |
| Review hidden inside Batch | **Disappears**; review is the main surface |
| Accept / Correct / Uncertain per dimension, optional note | **Survives** unchanged in meaning |
| "Agreement, not accuracy" and uncertain-excluded denominators | **Survives**, promoted into Insights and the report method line |
| Insights filter panel (views, metric, denominator, selection rule) | **Simplified**: scope plus group; advanced options move behind the table or report |
| Representative cases, context notes | **Survive** (cases in the report; notes as a project item) |
| "Inspect all model-native scores" disclosure | **Survives** as a disclosure in the AI record |
| Models and provenance panel | **Survives**, moved to the status bar or report footer and Help ▸ About |
| Temporary tokens, expiry, "Clear temporary data", capacity limits | **Disappear** (persistent projects) |
| Explicit CSV export | **Survives** as "Export reviewed dataset" and "Export insights" |
| Moderation Training, Support Triage tabs | **Leave the main navigation**; see section 6 |
| Flask web UI | Not part of the V2 product; frozen dev/compat surface until its own retirement gate |

## 6. Moderation Training / Support Triage disposition

- **P1, keep as one demoted native surface** (`s_practice_keep`). Both modes
  become two tabs in a separate Decision Practice window, reached only from
  Tools (A), Settings (B) or the bottom of the rail (C). It uses synthetic
  cases only, never touches projects, persists nothing, and is ported once and
  then frozen. Cost: a native UI port of two workflows whose services total
  about 2.9k lines.
- **P2, retire from the V2 product surface** (`s_practice_retire`). There is
  no port. Help ▸ About states they remain in V1 0.10.0 and the repository
  history. This gives the smallest, most coherent product and removes the
  "half the product is simulation" critique. It loses a portfolio talking
  point.

## 7. Recommendation

**Direction A (Evidence Workbench) as the skeleton, with two pieces of C**:

- C's keyboard focus review becomes a "Focus mode" inside A's Review queue
  (`F11` or a toolbar toggle).
- C's written report becomes A's Insights export or print view.

B's stage rail is not adopted. Its useful part, telling a new user what comes
next, is covered by A's empty states and the project Overview.

Reasons:

- A is the most native use of Qt Widgets, so it is the cheapest to build well.
- It scales from 12 to several thousand records without a redesign.
- It keeps the AI record and human judgment next to each other on every
  record.
- It makes review the thing you do anywhere, rather than a stage you reach.

C's focus mode addresses A's main risk, a cluttered table-only review, and
C's report gives portfolio reviewers a readable artefact.

**Decision Practice: P2 (retire)**, unless the owner values the portfolio
story enough to pay for a native port. The Product Scope Gate's "keep, fold,
demote" preferred keeping them; A8 explicitly reopened retirement, so this is
the owner's call.

## 8. Decisions that require the owner

1. **IA direction.** Approve "A + C focus mode + C report", or pick A, B or C
   as-is.
2. **Moderation Training / Support Triage.** P1 (one demoted native Decision
   Practice window, frozen) or P2 (retire from V2; remains in V1).

Everything else in sections 4 and 5 is a proposed default that can be changed
during implementation scoping without a gate. Examples: light theme only,
non-English rows excluded from insights by default, no Save button.

## 9. What this exploration does not do

- It does not touch `main`, the Application Foundation branch, `src/`, tests,
  dependencies, PROJECT_STATUS, or ROADMAP.
- It opens no PR.
- The prototype is not evidence of performance, accessibility, or LGPL
  compliance. Each of those belongs to its own later work.
