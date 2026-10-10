# M8 Track B — Native UI fidelity alignment: screen map, delta register and evidence

This record covers Track B of M8: aligning the native Windows desktop with the
approved Round 3 UI/IA reference. Track A (technical hardening) is a separate PR and
is not described here.

**Status: Track B implementation complete and awaiting independent review. Subjective
design fidelity: PENDING OWNER. Owner exploratory trial: PENDING OWNER.** No agent can
accept the visual result. Nothing in this record is a visual acceptance, an accessibility
acceptance, a model-quality claim or a release-readiness claim. M8 as a whole is not
complete.

The reference screenshots and the prototype are not copied into the repository. They
live on the sidecar branch `prototype/v2-ui-ia-exploration` at commit
`9543c9eb637475e3f87dad1110460f08eaba5200`, under `prototypes/v2-ui-ia/round3/`, and
are read with `git show`; that branch is not merged and was not touched.

## 1. Precedence applied

The binding [UI/IA decisions U1–U4](V2_UI_IA_DECISION.md) outrank the prototype:

- **U4:** `demo_mod.png` and `demo_tri.png` (Moderation Training, Support Triage) and the
  sidebar's "Decision practice" group with its PENDING badges are retired. They are not
  implemented and are not listed as gaps.
- **U2:** the prototype's "finished rows survive cancel / resume" is not implemented.
  Cancellation still commits nothing.
- **U1:** the project-centred IA, the V1 feature boundary and the separation of the
  immutable AI record from the human judgment are fixed and unchanged. Palette,
  typography, spacing and component styling were changed.
- Web-only chrome (the demo top bar, "Reset demo", the simulated title bar), the
  prototype's scripted numbers and web fonts are not requirements.
- No new metric, analysis feature, persistence semantic or Flask dependency was added,
  and `desktop/` still imports only `application` and `contracts`
  (`tests/desktop/test_boundaries.py`).

## 2. Screen map: reference to native

Native states are produced by `tests/visual/fidelity.py` on synthetic data (see
section 4). The window content area is 1358 × 803 at 100% scale, the reference's own
frame. The first-run and Models windows are dialogs and are captured at their own size
(1000 × 560 and 640 × 560), so their "900 px" pair is not a like-for-like reflow capture. File names follow the reference.

| # | Reference | Native screen and state | Capture |
| --- | --- | --- | --- |
| 1 | `demo_setup.png` | First-run setup window (models not installed), and the Models window with both ready | `demo_setup`, `demo_setup-ready` |
| 2 | `demo_projects.png` | Projects, three projects, nothing open | `demo_projects` |
| 3 | `demo_direct.png` | Analyze one text with a result; and the threshold-fallback state | `demo_direct`, `demo_direct-fallback` |
| 4 | `demo_import.png` | Import & validation of a CSV whose text column is `message_body` (one rejected row) | `demo_import` |
| 5 | `demo_results.png` | Results of an analysed project (46 analysed, 1 failed, 1 rejected) | `demo_results` |
| 6 | `demo_review.png` | Review, "Unreviewed" queue; and a record in an unsupported language | `demo_review`, `demo_review-language` |
| 7 | `demo_agreement.png` | Agreement with 29 reviewed records | `demo_agreement` |
| 8 | `demo_compare.png` | Insights · compare, grouped by `source_label`, three groups, agreement perspective | `demo_compare` |
| 9 | `demo_notes.png` | Insights · notes & cases | `demo_notes` |
| — | `demo_mod.png`, `demo_tri.png` | None. Retired by U4 | — |

Dataset differences that are not defects: the native datasets are invented and differ in
detail from the prototype's scripted numbers (the synthetic models are keyword stand-ins);
the prototype's `source_type` groups (`app_store`, `support`, `forum`) are `source_label`
values here, because `source_type` is a fixed vocabulary in the product; the OS window
frame is drawn by Windows, not by the app.

## 3. Method

- Captures use the real Windows Qt plugin (`platform: windows`), never `offscreen`. Each
  picture is `QWidget.grab()` of the application's own window.
- The window is created **unmapped** (`WA_DontShowOnScreen`): the Windows plugin lays it
  out and paints it, but it never appears on the desktop. This gives the reference's exact
  geometry (a mapped window is clamped to the screen, 1284 × 701 on the capture machine)
  and means nothing else on the desktop can be captured. A check on one screen found
  **0 differing pixels** between the mapped and unmapped grab at 1200 × 600.
- The data directory is a throwaway folder and the providers are synthetic.
- Before = the baseline `53a5c27` (the same harness copied into a baseline checkout);
  After = this branch's final behavioural head. Reference → Before → After pictures were
  each looked at as images.
- Interaction is proved by Qt regression tests under `QT_QPA_PLATFORM=offscreen`
  (section 7), not by the pictures.

## 4. Repeatable capture steps (Windows PowerShell)

From the repository root, with the `dev` extras installed in `.venv`:

```powershell
# real platform plugin: make sure no offscreen override is set
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
$env:PYTHONPATH = "$PWD\src"
$out = Join-Path $env:TEMP "sti-fidelity"

# the nine screens at 100% scale, 1358 x 803 (optionally name scenes to capture a few)
.\.venv\Scripts\python.exe tests\visual\fidelity.py "$out\after"
.\.venv\Scripts\python.exe tests\visual\fidelity.py "$out\after" review compare

# narrow window (reflow at the 900 px minimum)
$env:STI_CAPTURE_SIZE = "900x640"
.\.venv\Scripts\python.exe tests\visual\fidelity.py "$out\after-900"
Remove-Item Env:STI_CAPTURE_SIZE

# 150% scaling (logical size 1100 x 700)
$env:QT_SCALE_FACTOR = "1.5"; $env:STI_CAPTURE_SIZE = "1100x700"
.\.venv\Scripts\python.exe tests\visual\fidelity.py "$out\after-150" review projects direct
Remove-Item Env:QT_SCALE_FACTOR, Env:STI_CAPTURE_SIZE

# optional: shrink wide pictures, as the committed evidence was
$env:STI_CAPTURE_MAX_WIDTH = "1000"
```

The script prints `platform: windows`; an `offscreen` capture is not equivalent. To
recapture the Before set, check out the baseline in a separate directory, copy
`tests\visual\capture.py`, `fidelity.py` and `synthetic.py` over its own, and run the
same command from that directory:

```powershell
git worktree add --detach "$env:TEMP\sti-baseline" 53a5c27
Copy-Item tests\visual\capture.py, tests\visual\fidelity.py, tests\visual\synthetic.py "$env:TEMP\sti-baseline\tests\visual\"
Push-Location "$env:TEMP\sti-baseline"
$env:PYTHONPATH = "$PWD\src"
& "<path to the repository .venv>\Scripts\python.exe" tests\visual\fidelity.py "$out\before"
Pop-Location
git worktree remove --force "$env:TEMP\sti-baseline"
```

To extract a reference picture: `git show 9543c9eb637475e3f87dad1110460f08eaba5200:prototypes/v2-ui-ia/round3/shots/demo_review.png > demo_review.png`.

## 5. Delta register

Class: **(a)** legitimate UI-fidelity defect, **(b)** justified Qt-native or responsive
difference, **(c)** intentionally obsolete under U1–U4. Disposition: **FIXED**,
**ACCEPTED DEVIATION** (kept on purpose, reason given) or **UNRESOLVED** (needs an owner
decision; not changed in Track B). Impact: H visible structure, M visible detail, L polish.

### 5.1 Global

| ID | Delta (reference → Before) | Impact | Class | Disposition |
| --- | --- | --- | --- | --- |
| G1 | Light sidebar with a white active pill, a "No project open" header and a quiet model line → dark graphite sidebar with an edge bar | H | a | FIXED: light sidebar, pill, idle header, flat mono model status (still one button, same text and name) |
| G2 | Warm-grey paper with white sheets, near-black primary action → cream paper, ultramarine primary | H | a | FIXED: tokens re-set; every pair re-measured in `test_style_contrast.py` |
| G3 | Blue means "human" only → blue was also every primary action, blurring the AI/human distinction | M | a | FIXED: primary = ink; blue marks the human's own actions (Save and next, Add note) and chosen judgments. Checked boxes keep the blue check fill; the Review progress meter is slate like the reference's ink |
| G4 | Reference: tinted status chips; Before: outlined, untinted chips | M | a | FIXED: chips are now tinted (ready, caution, failure, human and machine tones), each with its word |
| G5 | Pill-track segmented tabs with counts → dark filled buttons | M | a | FIXED; wraps to a second line when narrow |
| G6 | Instrument Serif / Inter / IBM Plex Mono → Georgia / Segoe UI / Consolas | M | b | ACCEPTED DEVIATION: system fonts (U1). The OFL facts and the owner decision are in section 6 |
| G7 | Demo top bar, "Reset demo", simulated title bar and frame | — | b | ACCEPTED DEVIATION: web-only, OS draws the frame |
| G8 | Small glyph icons in the sidebar | L | b | ACCEPTED DEVIATION: iconography is not fixed by U1; labels carry the meaning |
| G10 | Quiet scrollbars in the reference → a visibly dark full-height thumb in the queue and the table | M | b | ACCEPTED DEVIATION: the thumb keeps the 3:1 control contrast (`LINE_STRONG`); a paler thumb would fail it |
| G11 | Sidebar counts Projects 3, Review 17 (unreviewed), notes 2 → Results 48 and Review 46, no Projects count | L | b | ACCEPTED DEVIATION: the counts are rows and reviewable rows; an unreviewed count would change what the badge means |
| G9 | "Decision practice" group, Moderation training, Support triage, PENDING badges | — | c | NOT IMPLEMENTED (U4) |

### 5.2 Per screen

| ID | Screen | Delta | Impact | Class | Disposition |
| --- | --- | --- | --- | --- | --- |
| S1 | Setup | Hero statement and explanation beside the model cards → a plain list in a small dialog | H | a | FIXED: two-pane first-run window; wording states only what the product does (one-time download from huggingface.co at pinned revisions, checked after download, damaged model never used, offline folder path) |
| S2 | Setup | Tinted "ready · verified" chips → outlined chips | M | a | FIXED (tone follows the readiness icon; the word is always written) |
| S3 | Setup | Model id, revision, licence and size always visible on the card → behind "Details and provenance" | M | b | ACCEPTED DEVIATION: M5.1 progressive disclosure; the same card serves the Models window. Easy to reverse if the owner prefers |
| S4 | Setup | "Licences…" link → none | L | b | ACCEPTED DEVIATION: no licence viewer exists; notices and the LGPL gate belong to M10 |
| P1 | Projects | One list card of rows, newest "Open" primary → separate bordered cards, every Open primary | H | a | FIXED |
| P2 | Projects | "Analyze one text" beside the main action → only Import | M | a | FIXED |
| P3 | Projects | Per-project ROWS and HUMAN REVIEW (segmented bar, "29 / 46 reviewed · 10 corrected"), "last opened", filter tabs All / In review / Fully reviewed → name and updated time only | H | a | FIXED in Round 2 (section 11) with these remaining choices: counts read at listing time with six small `COUNT(*)` queries (no text); a continuous progress meter with the numbers in words under it; tabs All / Not analysed / In review / Fully reviewed with counts (one more tab than the reference, so that an unanalysed project has a home); the row count is a line under the name, not a column with a header row; "last opened" is not shown because the product stores only created and updated times and the owner ruled out new persisted data (the updated time is shown instead); "corrected" follows the Review page's rule and can include a record that is not fully reviewed yet |
| P4 | Projects | "New project from CSV…" and a × delete → "Import CSV…" and "Delete…" | L | b | ACCEPTED DEVIATION: M4 wording and conservative delete wording (V2-1) |
| P5 | Projects | Storage path line (`%LOCALAPPDATA%…`) → a sentence without a path | L | b | ACCEPTED DEVIATION: no machine-specific path is shown |
| D1 | Direct | Input beside result → input above result | H | a | FIXED: two panes, stacked below 860 px |
| D2 | Direct | Large coloured label words and confidence → one line "Sentiment: Positive (82%)" | H | a | FIXED (polarity colour is never the only signal: the word and the confidence are written) |
| D3 | Direct | Limit chips (English only, 20,000-character limit, no truncation, not saved) → one sentence | M | a | FIXED: chips state facts the product enforces (V1 F1) |
| D4 | Direct | Threshold-fallback caution box → a muted sentence | M | a | FIXED: caution box only when the fallback chose Neutral |
| D5 | Direct | Character counter → none | L | a | FIXED |
| D6 | Direct | "Try an example" list → none | L | b | ACCEPTED DEVIATION: not in the F1 boundary; a prototype nicety |
| D7 | Direct | Vertical bars with a threshold line for the nine compact scores → horizontal bars | M | a | FIXED in Round 2: the Analyze page draws the nine scores as columns with their numbers and a dashed threshold line, named in full for assistive technology. Review's narrow AI card keeps the horizontal bar rows (ACCEPTED DEVIATION) |
| I1 | Import | A two-step wizard (read the file, name the project, then "Create project & analyze N rows") → the import creates the project at once | H | b | ACCEPTED DEVIATION: V2-1 and M4 persist the project at import; a confirm-before-create step would change persistence semantics |
| I2 | Import | Large valid / invalid / possibly-not-English figures → one text line | M | a | FIXED: figures; the language figure appears after analysis because the language check runs with the analysis |
| I3 | Import | Recognised metadata chips ("— not in file") → none | M | a | FIXED, with the note that groups come only from these columns |
| I4 | Import | A preview table of every row (id, text, source, check chip) with All / Invalid / Language notice tabs → only the rejected rows | H | a | FIXED in Round 2: every row, numbered from 1 for the first data row (as the Results table numbers rows), with a 100-character text excerpt, a Ready / Rejected check and the rejection reason, All / Rejected tabs, scrolling inside a bounded height. Choices: no source column (width; the metadata columns are shown as chips instead) and no Language notice tab (an obstacle: the language check runs with the analysis, so it is unknown at import) |
| I5 | Import | Wide reason column and scrollbar → squeezed table | L | a | FIXED (columns fit; the reason is elided with a tooltip) |
| R1 | Results | Big coloured sentiment counts over a proportional bar → three bar rows | H | a | FIXED: counts, share, stacked bar; exact text kept in accessible names |
| R2 | Results | Coloured sentiment words in the table → plain | M | a | FIXED (the word is written) |
| R3 | Results | A TEXT column (truncated record text) → no text | H | a | FIXED in Round 2: a read-only TEXT column from the same bounded excerpt; exports are unchanged |
| R4 | Results | Status chips ("analyzed", "fallback") in table cells → status words with a check mark | L | b | ACCEPTED DEVIATION: table cells are text; the word carries the state |
| R5 | Results | Vertical dominant-emotion chart, clicking a bar filters → horizontal bars, filters by combo | M | b | ACCEPTED DEVIATION (a choice, not an obstacle): the dominant-emotion card keeps bar rows with exact counts and shares and is filtered by the combo. The vertical chart was built only for Analyze one text (D7), where it is the main result |
| R6 | Results | Four cards in one row → three columns with the failed card under sentiment | L | b | ACCEPTED DEVIATION: reflows at narrow widths |
| V1 | Review | Queue of records with id and text excerpt, current line highlighted → none (a position counter and filters) | H | a | FIXED: queue pane over the existing filtered queue; a line opens its record by row identity; the open record stays selected after it leaves the filter |
| V2 | Review | Review-state tabs with counts and a progress bar → three combos | H | a | FIXED: tabs (All, Unreviewed, Reviewed, Corrected, Uncertain) with counts and a meter; the two AI filters stay as combos |
| V3 | Review | AI card and human card side by side from the first screen, AI tinted slate and human tinted blue → stacked below long headers; heavy outlines | H | a | FIXED: peer cards side by side whenever both fit (queue beside them if there is room too, else above), stacked at 900 px; card headings, large label words, tinted fills |
| V4 | Review | Accept AI / Correct / Uncertain as a segmented control → radio buttons in group boxes | M | a | FIXED: choice buttons that are still radio buttons (same names, same keyboard model) |
| V5 | Review | Previous / Next unreviewed at the record's top right; the record text as a large serif quotation → plain buttons at the bottom; body text | M | a | FIXED |
| V6 | Review | Language notice only when the text may not be English → a large panel for every record | M | a | FIXED: a quiet one-line check when supported; the full notice when not |
| V7 | Review | No compact-score bars on the AI card ("Inspect all 28" only) → sentiment and nine compact bars | M | b | ACCEPTED DEVIATION: F1.2 and M6 keep the compact scores visible; the page scrolls |
| V8 | Review | "Accept AI" → "Accept", plus Accept both / Save / Save and next | L | b | ACCEPTED DEVIATION: M5.4 behaviour and tests |
| A1 | Agreement | Open, very large numerals → boxed cards with smaller figures | M | a | PARTLY FIXED: figures enlarged to display size, still boxed and smaller than the reference; ACCEPTED DEVIATION for the rest |
| A2 | Agreement | Larger confusion cells → compact cells | L | a | FIXED |
| A3 | Agreement | A Sentiment / Dominant emotion toggle for the confidence panel; an export card with explanation → both panels shown; a header button and a checkbox | L | b | ACCEPTED DEVIATION: more information on one screen; M5.4 export copy |
| C1 | Compare | Numbered steps (01 Group by, 02 Perspective & metric, 03 Filters) → a flat list of fields | M | a | FIXED |
| C2 | Compare | Group cards side by side, each with name, a small-sample chip, a large figure, bar and counts → full-width text-heavy cards | H | a | FIXED: ReflowRow of cards (two across at 1358 px) |
| C4 | Compare | An "Export insights CSV…" button at the top right and a Compare / Notes tab strip → neither at the top (the export card is lower on the page; the sidebar chooses the view) | L | b | ACCEPTED DEVIATION |
| C5 | Results, Compare | A large language-check banner above the figures (reference: a per-row "fr?" chip) | L | b | ACCEPTED DEVIATION: V2-3 product honesty; it pushes the content down |
| C3 | Compare | Group chips and a segmented AI / Human / Agreement perspective → a checkbox list and a combo | M | b | ACCEPTED DEVIATION: the list is the accessible multi-select; changing the perspective control would churn M5.5 tests for no information gain |
| N1 | Notes | Association and value side by side; context tags as pills; notes under the form; cases first on the right → a long vertical form, a checkbox column, notes above the cases | H | a | FIXED |
| N2 | Notes | Case rule as tabs; "Reveal full local text" → a combo; the text shown | M | b | ACCEPTED DEVIATION: the reveal control is a web privacy affordance; the text is local and already shown elsewhere |
| N3 | Notes | Case text as a serif quotation, AI and human tinted | L | a | FIXED |

### 5.3 Behaviour checked

Keyboard and focus: the queue is one tab stop, Up and Down move a ring cursor without
opening anything, Enter and Space open the line under the cursor, and the open record is
drawn from its identity, so the highlighted line always equals the record shown.
Discarding unsaved edits is confirmed from the queue, the tabs, Previous, Next and the
filters, and a declined discard restores both the queue and the tabs. Choosing a line
from the queue keeps the keyboard on the queue, and a state refresh (a keystroke in the
note) does not scroll the queue back. The open line is named as open for assistive
technology. The existing focus-return, error-focus and review minimum-width tests pass
unchanged; `test_qt_reflow.py` is new and checks every page at 900 px and Review across
a sweep of widths.

## 6. Fonts: a separate note for the owner

The reference uses three web typefaces. The native product keeps system fonts. Where the
difference shows most: the display serif (Instrument Serif is narrower and higher-contrast
than Georgia, so titles and large figures look heavier and wider), the UI face (Inter vs
Segoe UI Variable: very close at 10 pt) and the letter-spaced mono eyebrows (IBM Plex Mono
vs Consolas). No fonts were bundled. Per the UI/IA record the licence claim is unverified;
bundling needs a decision by the owner and entries in
[Third-Party Notices](../THIRD_PARTY_NOTICES.md).

Licence facts, read in Round 2 from `https://raw.githubusercontent.com/rsms/inter/master/LICENSE.txt`,
`https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt` and
`https://raw.githubusercontent.com/Instrument/instrument-serif/main/OFL.txt` on 2026-10-09
(not legal advice):
Inter (`rsms/inter`), IBM Plex (`IBM/plex`, which covers IBM Plex Mono) and Instrument
Serif (`Instrument/instrument-serif`) are each under the SIL Open Font License 1.1.
Copyright lines: "The Inter Project Authors" (2016), "IBM Corp." (2017) and "The
Instrument Serif Project Authors" (2022). IBM Plex declares the Reserved Font Name
"Plex"; Inter and Instrument Serif declare none. The OFL permits bundling the fonts
with software if each copy carries the copyright notice and the licence text (as text
files or in the font metadata) and the fonts are not sold on their own; the fonts stay
under the OFL; a modified version may not use a Reserved Font Name. The Google Fonts
licence page for Instrument Serif was not read. Bundling is therefore plausible but is
an owner decision and a notices task; **no font was bundled**.

## 7. Interaction regression tests

All run under `QT_QPA_PLATFORM=offscreen` with real Qt widgets.

| Behaviour | Test |
| --- | --- |
| Queue lists the filtered records in row order and opens one by row identity | `test_qt_review.py::test_the_queue_lists_the_records_and_opens_one_by_its_row`, `tests/persistence/test_review_workflow.py` (queue tests) |
| A real mouse click on a queue line opens that record | `test_choosing_a_queue_line_with_a_real_click_opens_that_record` |
| Keyboard cursor vs open record; Enter and Space; one open line | `test_the_queue_keyboard_moves_a_cursor_and_enter_or_space_opens_a_line` |
| Unsaved judgment is confirmed before the queue, tabs or navigation discard it | `test_the_queue_asks_before_dropping_an_unsaved_judgment`, existing discard tests |
| State tabs carry counts and filter; a saved record stays in the queue | `test_the_review_state_tabs_carry_counts_and_filter_the_queue`, `test_a_saved_record_stays_selected_after_it_leaves_the_filter` |
| Controller `go_to` refuses a row outside the queue | `test_review_controller.py` |
| View model: queue, tabs, meter | `test_review_view.py` |
| Cards beside each other at 1280, stacked at 900, no horizontal scroll | `test_review_at_minimum_window_width_shows_both_records_without_horizontal_scroll` |
| Contrast of every new pair | `test_style_contrast.py` |
| Results figures and stacked bar | `test_qt_results.py` |
| Project list counts: read at listing time, no text column selected, six COUNT statements, a failing count degrades one row | `tests/persistence/test_project_listing_counts.py` |
| Review tabs filter the project list; Open by project id; filter kept and reset; compact rows at 900 px; keyboard focus kept through a refresh; no window flash while a row is built | `tests/desktop/test_qt_projects.py`, `tests/desktop/test_projects_view.py` |
| Import preview of every row, All / Rejected tabs, bounded scrolling height, 300-row import, markup in a tooltip shown literally | `tests/desktop/test_qt_results.py` |
| Bounded excerpts: tail of a long text absent, control and bidirectional characters removed | `tests/test_text_excerpt.py`, `tests/persistence/test_results_workflow.py`, `tests/desktop/test_results_view.py` |
| The nine compact scores as columns with a threshold, named in full | `tests/desktop/test_qt_navigation.py`, `tests/desktop/test_scores.py` |
| Owner scenario CSV imports as documented | `tests/test_owner_trial_scenario.py` |

## 8. Evidence index

Pictures are at 1000 px width. Directory `manual-qa/m8-visual-evidence/` (see its
[README](../manual-qa/m8-visual-evidence/README.md) for the index):

- `before/` and `after/`: the nine screens at 1358 × 803, plus the variants in section 2.
- `before-900/` and `after-900/`: the same at the 900 px minimum width.
- `after-150/`: Review, Projects, Analyze one text, Import and Results at 150% scaling.

Changed in Round 2: `after/`, `after-900/` and `after-150/` pictures of Projects, Import,
Results (now with `demo_results-table`, scrolled to the table so the TEXT column is
visible at every width) and Analyze one text (the columns chart). The `before/` sets are
the original baseline captures and were not regenerated. The Import preview shows its
first rows only at the narrow and scaled sizes; the bounded scroll is exercised by the
300-row test, not by a picture.

The reference pictures stay on the sidecar commit (section 1).

## 9. Not done, and decisions for the owner

- **Visual acceptance: PENDING OWNER.** The register above lists what was changed and
  what was deliberately kept; whether the result is close enough is the owner's call.
- **UNRESOLVED:** none from Round 1 remain. P3, I4 and R3 were built in Round 2
  (section 11) within the owner's constraints; no obstacle was met. The remaining
  ACCEPTED DEVIATIONS are listed in section 5.
- **Owner exploratory trial: PENDING OWNER.** See the
  [walkthrough](../manual-qa/owner-trial/WALKTHROUGH.md) and
  [friction log](../manual-qa/owner-trial/FRICTION_LOG.md). It is not M9's UAT.
- **Not covered by this track:** the queue's row geometry is in fixed pixels and does not follow a Windows text-size setting (DPI scaling is covered); formal accessibility acceptance, Narrator and
  high-contrast checks (M9); packaging and the LGPL gate (M10); a repeat on a second
  physical display or DPI beyond the 100% and 150% captures.
- Application-layer change: `ReviewSnapshot.queue` (read-only `QueueEntry`: row, record
  id, a 90-character excerpt, reviewed flag) exposes the existing filtered queue. No
  stored data, no schema and no rule changed.

## 10. Track B ledger

| Item | State |
| --- | --- |
| Branch | `milestone/m8b-ui-fidelity` from `origin/main` `53a5c27` |
| Capture harness | `tests/visual/fidelity.py`, `capture.py` (unmapped real-platform grabs, narrow and scaled options) |
| Demo helper | `tools/demo/` (launcher and invented CSV; dev/acceptance helper, no runtime dependency) |
| Owner trial files | `manual-qa/owner-trial/` (scenario CSV, walkthrough, friction log) |
| Closeout review | Independent Standards and Spec reviews ran as separate passes after Round 1 and again after Round 2; their findings were repaired test-first (see the PR) |
| Status files | `PROJECT_STATUS.md`, `ROADMAP.md`, `README.md` and `DEVLOG.md` carry the M8 Track B row in the governance commit that follows CI |
| Implementation head, governance head, CI | in the PR description and the Track B validation row of `PROJECT_STATUS.md` |

## 11. Round 2: owner instruction to close P3, I4 and R3 (slice ledger)

After Track A merged (PR #50, `origin/main` `1a48d25`), the owner asked for higher
fidelity and for the three items that Round 1 left UNRESOLVED to be built within
these constraints: existing project data only; bounded read models; no schema change,
no new persisted summary, no new analytics; no network; list text limited to a sanitized
excerpt of at most 100 characters (a record shorter than that may be shown in full);
nothing logged; exports unchanged; UI thread never blocked.
Track A's wording stays coherent: rows rejected at import are `invalid_rows`, analysis
failures are `failed_rows`, and analysed + failed = valid (A6).

Slices, each test-first. The seam named is where the failing test is written before
the code:

| Slice | What | Seam of the failing test |
| --- | --- | --- |
| P3a | Per-project counts in the project list (rows, rejected, analysed, reviewed, corrected) as a read-time summary: a handful of `COUNT(*)` queries inside the listing's existing read transaction, no text, no JSON, no full workspace load; computed in the same worker-thread listing the app already runs | `tests/persistence/test_project_listing_counts.py` (real SQLite repository: import, analyse, review, list) |
| P3b | List view model: row line, review progress, review state (not analysed / in review / fully reviewed) and the filter tabs with counts | `tests/desktop/test_projects_view.py` (Qt-free) |
| P3c | Project list widgets: progress meter and text per row, state tabs filtering the list, Open still opens by project id, accessible names | `tests/desktop/test_qt_projects.py` (real clicks) |
| I4 | Import validation: a read model of every row (row, id, a 100-character excerpt, ready or rejected with its reason), the table with All / Rejected tabs, scrolling inside a bounded height | `tests/persistence/test_results_workflow.py`, `tests/desktop/test_results_view.py`, `tests/desktop/test_qt_results.py` |
| R3 | Results: a truncated read-only TEXT column from the same bounded excerpt | `tests/persistence/test_results_workflow.py`, `tests/desktop/test_results_view.py`, `tests/desktop/test_qt_results.py` |

Existing tests that encoded the old "read models never hold record text" boundary
(`SENTINEL not in ...`) are revised deliberately, not weakened by accident: the text
may appear only as a bounded excerpt in the row read models and the table, and must
still be absent from every notice, error and export-independent surface.


### 11.1 Outcome

- **P3 (project list):** `ProjectSummary` gains read-time counts (`row_count`,
  `rejected_rows`, `analysed_rows`, `reviewed_rows`, `corrected_rows`), filled by five
  `COUNT(*)` queries over the identity, status and judgment columns inside the
  listing's existing read transaction. No text, report or note is read and nothing is
  decoded or persisted; no schema change. The listing already runs off the UI thread
  (`ProjectsController.refresh` through the job runner) and already opened each project
  file to read its name; that cost is unchanged apart from the five small queries.
  `test_listing_reads_counts_without_loading_any_record_text` traces the SQL and fails
  if a text column is selected. Track A's rules hold: a project held by another window
  is still skipped as before, and the counts use `invalid` for rows rejected at import
  and `analysed` for rows with a result, so analysed + failed = valid (A6) is untouched.
- **I4 (import preview) and R3 (results text):** the workflow read models carry
  `ValidationRow` / `ResultRow.excerpt`, produced by
  `application/text_excerpt.py` (whitespace folded, cut at 100 characters, `(empty)`
  for an empty text). A row read model carries only that sanitized excerpt, at most 100
  characters; a record shorter than the limit is shown in full, a longer one is cut.
  A test checks that the tail of a long text is absent from every read model and view. Notices,
  errors and exports are unchanged. The tests that used to assert "no record text in the
  read models" were revised to assert the bounded excerpt instead.
- **Selection integrity and UI:** the queue and tabs are unchanged; project rows open by
  project id (`test_the_review_tabs_filter_the_list_and_open_still_opens_the_right_project`);
  rows fall back to a compact layout below 760 px; the 900 px sweep and the list page at
  900 px pass.
- **D7:** the nine compact scores of Analyze one text are columns with a threshold
  line (`ColumnChart`); the narrow Review card keeps bar rows.

Cell text is cut at the column width on screen (about 28 characters at the default
column widths); the tooltip carries the full 100-character excerpt, escaped so record
text is shown literally and never as markup. A project whose analysis ran but produced
no result is labelled "Analysis ran · no row succeeded", not "Not analysed yet".
A count that cannot be read degrades that one list row instead of hiding the project.

### 11.2 Round 2 re-audit against the Reference

High-impact structural differences still present after Round 2, each deliberate:
Agreement keeps boxed figure cards and shows both confidence panels at once (the
reference toggles one); Compare keeps a combo for the perspective and a checkbox list
for the groups (the reference uses segmented tabs and chips); Notes keeps a combo for
the case rule; Review's AI card keeps the compact bar rows beside the scores the
reference hides behind "Inspect all"; Results keeps three card columns (the reference
has four); the sidebar has no icons. None hides data or breaks a binding decision; each
trades a visual match for information, keyboard operation or reflow. Typography is the
largest remaining material difference and is system-font bound (section 6).


## 12. Follow-up: the demo launcher may not delete what it does not own

An external review found that `tools/demo/launch_demo.py` called `shutil.rmtree` on a
caller-supplied `--root` on `--reset`, or when its seed marker was missing, whatever the
directory held. Fixed test-first. The seam is the launcher module itself, imported by
path with no Qt: `prepare_workspace(root, ...)` decides and prepares the folder, and
`main(argv, real_app_data=...)` returns the exit status, both before Qt is loaded.

Rules: automatic cleanup only in a directory that carries the tool's ownership sentinel
(`.sti-demo-workspace`, written before any seeding, so an interrupted seed is still
recognised), and then only the known tool-created children (`projects`, `models`,
`locks` and the marker) are removed, never an arbitrary tree. Refused with exit status 2,
a plain explanation on stderr and nothing deleted: a non-empty folder without the
sentinel, an unknown entry next to the tool's own, a file, a drive, home or repository
root or anything that contains the repository or the home folder, a parent of or place
inside the real application-data folder, a symlink or junction (on the root or a tool
child), and the real folder itself. A missing or empty root is created and claimed. An
older `_local/demo` made before the sentinel existed is refused until it is deleted by
hand. Tests: `tests/tools/test_launch_demo_safety.py`.

**Corrected wording.** The guarantee about record text is this: Results, Import and
Review lists carry a sanitized excerpt of **at most 100 characters** (90 in the Review
queue); a record shorter than the limit may be displayed in full. Earlier statements
that whole record text can "never" enter a view model were too absolute and have been
corrected. The Review page itself, as before, shows the open record in full.

**Python 3.12 teardown crash.** A CI run on head `cb84d37` ended with a segmentation
fault at interpreter exit ("shared QObject was deleted directly") after every test had
passed. It is **not conclusively root-caused**. A test that left a parentless widget
alive was fixed as the likeliest cause and the next run was green. It will be
investigated only if the same warning or crash recurs.

### 12.1 Preflight before any deletion

A second review found that a sentinel-marked workspace with a wrongly typed known child
(for example `projects/` a directory but `models` a regular file) could lose `projects/`
before the launcher failed on `models`, and that the sentinel's own type and content were
not checked. Seam, again `prepare_workspace` (no Qt): a complete read-only preflight now
runs before the first deletion. It requires the sentinel to be a regular file, not a link
or folder, holding exactly the text the tool writes; every known child that exists to
have its expected type (`projects`, `models`, `locks` folders; the marker a regular file)
and not to be a symlink or junction; and no unknown entry. Any malformed layout is refused
(exit 2, message on stderr) with the whole tree unchanged, well-typed siblings included.
Regression tests in `tests/tools/test_launch_demo_safety.py` snapshot the tree byte for
byte before and after each refusal.
