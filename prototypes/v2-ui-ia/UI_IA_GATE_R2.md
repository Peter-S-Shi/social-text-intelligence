# V2 UI/IA exploration, round 2: Human Gate brief

Round 1 ([UI_IA_GATE.md](UI_IA_GATE.md), directions A, B and C) was rejected
by the owner as too close to V1: the same near-white cards, the same green,
and the same web-form vocabulary rearranged into panes. Round 2 discards the
V1 visual language entirely.

Three directions follow, each with its own art direction **and** its own
structure. The fixed V2 constraints are unchanged:

- Windows-first PySide6 Qt Widgets;
- persistent local projects;
- review at the centre;
- the immutable AI record kept apart from human judgment;
- honest headline semantics;
- no Flask.

Synthetic data only. Screens are in [screenshots/](screenshots/) (`d_*`, `e_*`,
`f_*`). Run with `run_prototype.py --variant D` (see [README](README.md)).

## What changed from round 1

- **A visual identity, not a theme.** Each direction has a deliberate type
  system using fonts that ship with Windows:
  - Bahnschrift for display and condensed labels;
  - Sitka for serif text;
  - Cascadia Mono for provenance and data;
  - Segoe UI Variable for interface text.

  It also has a restricted palette with one signal colour. A shipped build
  could bundle OFL fonts instead.
- **The whole project is always visible.** The *evidence strip* (one tick per
  text in import order) shows the state of every text at once:
  - colour: agreed, overruled, unsure, open, or failed;
  - height: how unsure the machine was.

  Round 1 hid this behind counts.
- **The machine's doubt is a first-class visual, not a warning badge.** This
  covers the sentiment scale with the AI needle and your marker, the emotion
  rose with its 0.50 threshold ring, and the unsettled zone (margin < 0.30).
- **Calibration replaces dashboards.** Agreement is shown by machine
  certainty band, which is the honest form of "how far can I trust it on my
  text" and directly serves the Q5 evidence gate.

## Three directions

| | D. Casebook | E. Instrument | F. Field |
| --- | --- | --- | --- |
| Art direction | Editor's casebook: warm paper, black ink, one red pen; serif exhibits, condensed caps | Dark measurement console: graphite, amber = machine, mint = you, coral = disagreement; mono everywhere | Bold light graphic: white field, ink marks, vermilion crosses, electric-blue interaction |
| Metaphor for review | You **rule** on the machine's reading: uphold / overrule / abstain in red pen; the machine's reading is pencil marginalia | You **operate** an instrument: readout panels plus big keycaps (1 to 3, Q to C), commit with Enter | You **select a region** of the field (e.g. the unsettled zone) and judge it as a card stack |
| Project home | Typographic index of casebooks, each with its evidence strip; loose sheet for quick analysis | Single window with three modes (REVIEW, INGEST, CALIBRATE) under one strip and a `:command` line | The field itself: lenses on the left, field in the centre, "what the field says" brief on the right |
| Batch / import | Intake slip written as a sentence ("Read the text from [message_body], group it by [channel]"); live reading strip; "stop after this text" | Recording metaphor: big meters, live strip filling, log; "STOP · KEEP 87" | New texts land on the field as rings while the import runs |
| Insights | Findings as written front matter: one honest sentence, giant numerals, agreement by certainty band, overruled quotes | Calibration: segmented band meters, agreement ring, machine × operator matrix, per-channel strips | Small multiples of the field per group; groups with n < 20 are refused, not drawn |
| Quick analysis | Loose sheet: read one text without filing it | `:analyze <text>` probe overlay that also says how often texts read this way were overruled here | Probe: "where would this text land?", a pin on the field with that region's overrule rate |
| First run | "Before the first reading": models cited like a bibliography | Reader rack with VU-style meters per model | Empty field: "the field fills once the two readers are here" |
| Strongest at | Identity, trust and readability; portfolio impact; honest language | Throughput, keyboard flow, long sessions, density | Insight: shows where the model fails on *your* text; the most original IA |
| Weakest at | Density for very large projects; serif-heavy screens need care at small sizes | Can feel cold or "pro-tool" to newcomers; dark-only identity | Review of individual texts is one step removed; the field's V-shape is partly geometry (polarity and margin are related), so it needs explanation |
| Qt cost | Medium: mostly labels plus two painted widgets | Medium to high: many painted widgets, a command line | High: an interactive scatter with selection, hit-testing and annotations |

## V1 concepts: survive or disappear (round 2 view)

This updates round 1 section 5 where they differ.

| Change | What happens in round 2 |
| --- | --- |
| Gone | Cards on near-white with one green accent; four peer tabs; numbered 1-2-3 Batch page; filter-form Insights; expiry and temporary-token language |
| Kept and reshaped | Accept / Correct / Uncertain become uphold / overrule / abstain (D), keycaps (E), or judge buttons (F), with the same meaning and the same separate storage |
| Kept and reshaped | "Agreement, not accuracy" becomes **calibration by certainty band** in all three directions |
| Kept and reshaped | Threshold-fallback explanation becomes the dashed 0.50 ring on the emotion rose plus plain-language readings |
| Kept and reshaped | Preview and validation, and row-level failure isolation, become the intake sentence (D), meters and log (E), or the side sheet (F) |
| Kept and reshaped | Provenance becomes a quiet mono footer, never a panel |

## Recommendation

**D (Casebook) as the product's identity and review surface, with two
elements absorbed:**

- **The field from F** becomes the centrepiece of D's Findings and an entry
  point: "select the unsettled zone, then rule on it".
- **The keyboard grammar from E** becomes D's shortcuts (`U`/`O`/`A`, `1`-`3`,
  `Q`-`Y`, Enter). D already carries E's evidence strip.

Reasons:

- D is the one a portfolio reviewer remembers. It looks like nothing else in
  the category, which is the opposite of mediocre.
- Its metaphor (machine reading vs. human ruling) *is* the V2 thesis, so the
  separation between the AI record and human judgment is felt, not explained.
- It stays legible and calm for the owner's real reviewing.
- The field gives D a genuinely new insight surface.

E is the right choice if the owner values reviewing speed and density over
identity. F alone is the most original but leaves review one step removed from
the text.

## Decisions for the owner

1. **Art direction and IA.** Choose one:
   - D + F field + E keys (recommended);
   - D, E or F as-is;
   - another combination. Name it in terms of the screens, for example
     "E's review with D's findings".
2. **Moderation Training / Support Triage** (carried from round 1, still
   open):
   - P1: one demoted native Decision Practice window;
   - P2: retire from V2.

   Recommendation: P2. If P1 is chosen, it adopts the chosen direction's
   style.

Proposed defaults that do not need a gate:

- light identity for D and F, dark for E;
- no Save button;
- non-English rows marked and excluded from insights by default;
- groups with n < 20 not drawn as rates.

## Scope reminder

Sidecar prototype only. No changes to `main`, the Application Foundation
work, `src/`, tests, dependencies, or lifecycle files, and no PR.
Accessibility (contrast of the pencil and faint tones, keyboard focus order,
screen-reader names for painted widgets) and LGPL compliance are not assessed
here. Each chosen direction must pass both later.
