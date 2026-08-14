# Synthetic Text Samples for Manual Review

This directory contains project-authored synthetic material for manual
acceptance review of Social Text Intelligence 0.10.0. It contains no real
messages, names, accounts, organizations, or platform data.

## Sample dependency audit

| Product area | External text needed? | Recommended sample | Why |
| --- | --- | --- | --- |
| CLI `about` and `contracts` | No | None | These commands describe the package and contracts. |
| Direct analysis | Yes | `sample-data/direct_text_cases.md` | Short, varied English text is easiest to enter one case at a time. |
| Batch CSV | Yes | All three CSV files | The workflow needs valid UTF-8 CSV input, text-column selection, and row-level error cases. |
| Human Review | Yes, through a completed batch | `sample-data/review_insights_workflow.csv` | Only successfully analyzed rows enter the review queue. |
| Insights & Community Context | Yes, through a completed batch | `sample-data/review_insights_workflow.csv` | Trusted metadata and deliberate group sizes are required to test grouping and sample safeguards. |
| Moderation Training — built-in cases | No | Packaged cases | The repository already contains 20 synthetic moderation cases. |
| Moderation Training — workspace cases | Yes, through a completed batch | `sample-data/review_insights_workflow.csv` | Only successfully analyzed batch records can be prepared as workspace cases. |
| Support Triage — built-in tickets | No | Packaged tickets | The repository already contains 22 synthetic support tickets. |
| Support Triage — workspace tickets | Yes, through a parsed batch | Main and edge-case CSV files | Successfully parsed rows remain eligible even when NLP inference fails. |

## Files and intended use

## Directory governance

- `manual_review_questionnaire.html` is the tracked bilingual, offline review
  form. Its sidebar and previous/next controls support long review sessions.
- `sample-data/` contains only tracked project-authored synthetic inputs.
- `guidance/` contains tracked instructions and sanitized handoff records.
- `results/` is deliberately ignored by the repository `.gitignore`. Keep raw
  questionnaire JSON, screenshots, exports, notes, and machine-specific paths
  there. Never force-add this directory to Git.

Open the questionnaire directly in a browser. Save every new export under
`manual-qa/results/`, then provide that local file to the reviewer without
staging it. The questionnaire may store an in-progress copy in browser local
storage; the JSON export remains the portable review record.

### `sample-data/direct_text_cases.md`

Ten compact English cases for the Direct analysis page. They cover clear
polarity, neutral information, mixed wording, negation, polite criticism,
sarcasm-like wording, multi-emotion language, and context ambiguity. The
observations are not ground-truth labels; they are prompts for checking whether
the interface remains transparent and plausible.

### `sample-data/review_insights_workflow.csv`

Twenty valid English records for the main end-to-end review:

- `account_access`: 4 records — deliberately below the insufficient-sample
  threshold of 5;
- `billing`: 6 records — deliberately within the 5–9 small-sample range;
- `service_reliability`: 10 records — large enough for ordinary descriptive
  comparison;
- varied source, community, month, and parent-record metadata;
- varied positive, negative, neutral, and mixed wording.

Use this one upload for Batch CSV, Human Review, Insights, workspace-derived
Moderation Training, and workspace-derived Support Triage. Review at least five
records definitively to exercise confidence-band comparison. Review all twenty
only when testing complete group-level human perspectives.

### `sample-data/alternate_text_column.csv`

Five valid records whose text field is named `message`. This verifies explicit
text-column selection and reporting of the unsupported `demo_extra` column.

### `sample-data/batch_validation_edge_cases.csv`

Nine rows designed to remain safe and auditable:

- 2 ordinary successful English records;
- 1 structurally valid French record that should remain parsed but fail
  English-only model analysis;
- 2 rows sharing a duplicate supplied ID;
- 1 empty-text row;
- 1 unsupported `source_type`;
- 1 invalid timestamp;
- 1 invalid language tag.

Expected preview: 3 valid rows and 6 invalid rows. Expected completed analysis
with the approved English-only providers: 2 successful rows and 7 failed rows.
The French row is useful for verifying that Support Triage may explicitly
snapshot a parsed record even when NLP analysis failed. It should not be
eligible for workspace-derived Moderation Training.

## Safe-use rules

- Treat model predictions as estimates, not ground truth.
- Do not replace these records with real messages during repository review.
- Exported review files may contain human notes and should remain local unless
  separately privacy-reviewed.
- To test spreadsheet-formula protection, type
  `=SYNTHETIC_FORMULA_TEST` into a review note in the application, then verify
  the exported cell begins with an apostrophe. The sample CSV files themselves
  intentionally contain no executable spreadsheet formulas.
- Workspace state is process-memory only. Export before clearing the workspace,
  allowing it to expire, or closing the server.
- Submit exactly the same characters when comparing repeated model results.
  Adding arrows or other punctuation changes the analyzed input and may cause a
  small legitimate score change even when the compact label stays the same.
