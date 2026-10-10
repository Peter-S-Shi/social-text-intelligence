# M9 — Representative-domain evaluation protocol

## Registration and authority

This is the owner-approved M9.0 design for Q5 (Gate PASS 2026-10-10), governed by the
[evidence contract](V2_M9_EVIDENCE_CONTRACT.md). English software/app feedback and
Strategy A are owner-approved. **The targets of 180 real primary records,
45 separate synthetic challenge cases and at least 60 double-blind human
references received owner M9.0 Gate approval** (reviewed design HEAD `32d8d37`);
they are not acquired data or proof of source or annotator availability.
No sources, annotations or predictions are produced here.

Design freeze occurred at recorded M9.0 owner approval on 2026-10-10. The later M9.2 execution
freeze binds sources, frames, dates, seeds and IDs before labeling/predictions.
Both freeze records must identify versions, reviewer/owner roles and amendment
history. Source permissions precede retrieval; see the contract's intake gate.

## Approved target sample design

| Source-channel stratum | Primary real target | Synthetic challenge style target |
| --- | ---: | ---: |
| Public app/product reviews: user app/software assessments | 60 | 15 |
| Technical support/issue feedback: service or feature experience reports | 60 | 15 |
| Software/community discussion: reactions about app/software use | 60 | 15 |
| Total | 180 | 45 |

Channels describe origin, not sentiment labels. Freeze a precedence rule for
overlapping sources in the execution manifest; assign each record to exactly
one channel. Equal channel allocation provides comparisons, not industry
prevalence. Stop for a prospective owner-approved amendment if any channel
cannot lawfully supply its target, **before labels or predictions are inspected**.
Do not shrink n for favorable scores, substitute synthetics or relabel unrelated
corpora as app feedback. Confirm independent second-annotator availability before
locking the execution plan; unavailable independence requires owner escalation,
not AI-generated agreement.

### Eligibility, sampling and denominators

Eligible records must be authentic, authorized for the study, English, and about
expressed software/app experience within registered source/date/channel rules.
The written rules exclude inaccessible/unsafe, non-English, withdrawn-consent,
unrelated and duplicate material without consulting predictions or appraisal
labels. Short authentic records remain eligible and form a documented slice.
An otherwise eligible oversize/model-capacity failure remains in the eligible
sample and coverage ledger, not an excuse to sample a replacement.

Execution registration must fix source/date frames, inclusive eligibility rules,
screening method, normalization/dedup algorithm and near-duplicate criterion,
cross-channel dedup precedence, random generator/version/seed and selection
method. Deduplicate exact and near-duplicates across channels before random
selection; keep a count ledger and deterministic canonical-member rule independent
of labels/easiness. Select uniformly without replacement within each eligible
channel frame. Do not balance sentiment, select easy examples or filter by AI.
Freeze all selected IDs and the dual-label subset before annotating or inference.

Register frame size, each screening exclusion with reason, eligible-frame size,
selected eligible n per channel, and attempted/inferred counts. Source withdrawal
after freeze is logged against the original denominator with no silent replacement;
follow privacy/takedown obligations and prospectively amend if needed. Record
normalization errors, language warnings, input-too-long, runtime/crash and missing
predictions. Do not reclassify difficult selected records as ineligible after
seeing outputs. The planned 180 is not a claimed available sample.

### Challenge cases and record manifest

The future 45 `SYNTH_CHALLENGE` cases cover sarcasm/irony, mixed valence, polite
complaints, missing context, implicit appraisal, jokes, unsupported languages,
short text and high-emotion/low-sentiment divergence. Freeze intent and expected
behavior before outputs; expected error/warning behavior is distinct from an
accuracy label. Report challenge cases separately from `REAL_PRIMARY` and
`SYNTH_UAT`. Do not quietly reuse the M8 trial as independent gold.

Each record manifest includes pseudonymous ID, data class, channel, permitted
provenance reference, date/version context, eligibility/reason, annotation and
rule version, uncertainty/reason, inference status/error, exact model revisions,
preprocessing/mapping/threshold version and exclusions. A restricted manifest
holds source-record links. Public manifests/reports must pass rights and privacy
review; a digest provides integrity, not rights or anonymity by itself.

## Independent human reference annotation

Create and version a guide with neutral, author-created examples before labeling.
Label blind to AI labels/scores, confidence and STI's model-first Review screen.
App `Accept`/`Correct`/`Uncertain` actions prove workflow behavior, not independent
gold. AI/LLM-assisted experiments cannot be counted as blind human references.
Freeze reference labels and adjudication before unblinding predictions.

Sentiment targets expressed appraisal of the software/app experience, never the
writer's mental state. Factual description without appraisal can be `neutral`.
Use exactly `positive`, `neutral`, `negative`, or `UNCERTAIN` with reason.
`UNCERTAIN` is reference status, not a fourth model label.

Emotion references use one dominant of `joy`, `amusement`, `admiration`,
`gratitude`, `anger`, `sadness`, `fear`, `disgust`, `neutral`, plus zero or more
distinct non-neutral secondaries, or an emotion `UNCERTAIN` status/reason.
Dominant cannot repeat as secondary; `neutral` has no secondaries. Label explicit
or strongly supported expression, with a written ambiguity/dominance rule; do
not reverse-engineer human labels from the classifier threshold. When dominant
or the complete set cannot be resolved under the guide, the emotion reference
remains uncertain for both emotion analyses. Sentiment certainty is independent.
Record context gaps, sarcasm, mixed signals and sentiment/emotion divergence.

Approved independent review target: draw 20 IDs without replacement per channel (at
least 60/180 total), register this subset before predictions, and have two human
roles label independently and blind to one another. The remaining 120 are not
independently corroborated. Keep original labels, disagreement reasons and
blinded adjudication/version history. Use a documented blinded adjudicator or
blinded consensus procedure; unresolved cases remain `UNCERTAIN`. Do not use AI
as the second annotator or silently relax the design.

Report pre-adjudication sentiment observed agreement and Cohen's kappa where
computable; for emotion, exact non-neutral set agreement, mean Jaccard and
label-wise agreement/support. Two empty sets have Jaccard 1 by convention. Report
assigned dual subset size, completed pairs, task-definitive pairs, uncertain
pairs, per-channel counts, and the actual denominator of each statistic.
Agreement calculations requiring definitive labels use task-definitive pairs;
uncertainty/disagreement exclusions remain adjacent. Kappa undefined from zero
variation or no pairs is `not estimable`, not perfect agreement.

## Exact shipped prediction semantics

| Task | Immutable evaluated model |
| --- | --- |
| Sentiment | `cardiffnlp/twitter-roberta-base-sentiment-latest@3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` |
| Emotion | `SamLowe/roberta-base-go_emotions@d75048347613a25d77de8cf6412eaae9fa7b26be` |

Use production normalization and the audited compact mapping. Record application
SHA, package/Python/runtime/tokenizer versions, analysis mode, full model
revisions, mapping/guide versions and configuration. Approved evaluation mode
is the shipped combined analysis with audited default inclusive threshold `0.5`;
record the actual value and do not tune it for M9. The two providers have a
512-token encoded-input budget with special tokens and no truncation; the
20,000-character application ceiling is distinct. Combined preflight rejects an
over-budget row before either model, leaving no partial report. An English
eligible row with an unsupported/undetermined language warning remains counted;
language scores are detector evidence, not accuracy probabilities.

Sentiment selects the largest native negative/neutral/positive probability with
one-to-one mapping. Emotion preserves all 28 native scores and uses max within
the [audited compact groups](EMOTION_MODEL_AUDIT.md). Eight unmapped native labels
remain visible but do not become compact classes. The highest active non-neutral
compact score is dominant; other active scores are secondary, sorted by
descending score then label for ties. If none is `>= threshold`, dominant is
`neutral` and secondaries are empty. Multi-label scores are independent, not a
distribution summing to 100%, and confidence is not calibrated correctness.

Do not change model, taxonomy, mapping, threshold or preprocessing to improve
results. A change needs a separate approved model/product audit and new
prespecified evaluation, not a post-hoc adjustment to this study.

## Task-specific denominators and uncertainty

For each channel and overall, define the following ledger; never use a single
jointly definitive row count for every task:

| Symbol | Definition |
| --- | --- |
| `N` | Selected pre-model eligible records, including every attempted row and later failure/withdrawal (target 180 overall) |
| `D_s` | Records with definitive sentiment reference |
| `D_d` | Records with definitive dominant-emotion reference |
| `D_e` | Records with definitive complete non-neutral emotion-set reference |
| `P_t` | Eligible rows with a valid shipped prediction for task `t` |
| `M_t` | Intersection of `D_t` and `P_t`, the task metric denominator |

Under this guide complete definitive emotion is required, so `D_d = D_e`; still
report the two task denominators separately. Sentiment can be definitive while
emotion is uncertain, and vice versa. A future partial-reference scheme would
require a prospective amendment. Application whole-record Review completion
does not define reference eligibility. Combined inference normally gives the
same successful rows for both tasks; preserve task counters rather than assuming
that equality under every failure.

Beside **each** headline metric report `N`, `D_t`, `N - D_t` by uncertainty or
missing-reference reason, `P_t`, `M_t`, definitive-reference coverage `D_t/N`,
inference coverage `P_t/N`, metric coverage `M_t/N`, and failures among definitive
rows `D_t - M_t`. Distinguish unresolved annotation, withdrawals and genuinely
missing labels; do not call every missing label `UNCERTAIN`. Count overlapping
reasons explicitly without double-counting totals. Accuracy metrics use only
`M_t`, never silently treat failed predictions as correct or invent their class.
Successful predictions with uncertain gold remain in coverage/error analysis.
Publish channel/label composition of definitive subsets and report empty subsets
as `not estimable`.

## Mandatory analysis outputs

| Task | Headline metrics | Supporting outputs |
| --- | --- | --- |
| Sentiment | Macro-F1 over fixed three classes | Confusion matrix, per-class precision/recall/F1/support, accuracy, channel splits |
| Dominant emotion | Macro-F1 over fixed nine labels including neutral | Confusion matrix, per-class precision/recall/F1/support, channel splits |
| Compact non-neutral sets | Micro-F1 and Macro-F1 over fixed eight non-neutral labels | Per-label precision/recall/F1/support, exact set match, empty-reference/predicted-set prevalence, channel splits |
| Coverage | Task-specific denominator ledger above | Every failure/exclusion reason, warnings, input-too-long and short-text slices |
| Errors | Taxonomy, not a score | Sarcasm, mixed valence, jargon, context ambiguity, mapping/fallback, short text, emergent failures |

For set comparison map human/predicted `neutral` fallback to the empty
non-neutral set. Dominant analysis remains nine-way and separate. Exact set
match counts two empty sets as a match, and their prevalence must be shown so
fallback does not inflate an unexplained headline. Preserve all eight labels in
macro metrics, including zero-positive-support labels. Approved convention:
zero precision/recall/F1 denominators yield 0 with support shown; an entirely
empty task subset yields no estimate. Unsupported classes do not support
capability claims about those classes. Report unweighted counts/matrices with
their actual n beside weighted aggregate estimates.

Overall study estimates use equal channel weight, not deployment prevalence.
For pooled metric calculations on available `M_t`, each channel's contributing
records receive total weight 1/3 (each row weight `1/(3 * n_channel,t)`). Compute
weighted confusion counts or label TP/FP/FN first, then P/R/F1; do not substitute
the mean of channel F1 for pooled F1. Show raw channel metrics as well. If a
channel has no contributing definitive successful rows, the planned equal-channel
estimate is not estimable; do not renormalize over remaining channels silently.
Reference/inference coverage still uses original `N`, not these metric weights.

Approved finite-sample uncertainty method: 2,000 fixed-seed stratified bootstrap
resamples with replacement within each channel, 95% percentile intervals,
recomputing weights and metrics in each draw. Register generator/version/seed
before labels/predictions. Resample whole record units to retain within-row
label dependence. Metric intervals describe conditional `M_t` evidence, not
failed/uncertain rows; show their coverage limits. Report non-estimable draws and
do not hide unsupported labels or sparse per-channel support. These numerical
analysis defaults were owner-approved at M9.0 alongside the target sample budgets.

## Report and claims

Report lawful source coverage, frame and selected counts, annotation independence,
adjudication/uncertainty, exact shipped configuration, all required metrics,
negative findings, failure slices, uncertainty and limitations. Keep challenge
results separate. Include a `SUPPORTED` / `UNSUPPORTED` / `INSUFFICIENT EVIDENCE`
claims table and trace each statement to its task/sample/coverage.

There is no arbitrary F1 pass bar. Credible measurement and acceptable user-facing
claims are separate decisions. Weak scores are valid findings; severe systematic
misleading behavior is an M9.4 product-acceptance risk. Broad claims such as
"highly accurate", "reliable" or "fit for all feedback" cannot follow from an
equal-channel study with sparse labels, uncertain references or source mismatch.
The [exit gate](V2_M9_EXIT_GATE.md) defines evidence completion and owner synthesis.
