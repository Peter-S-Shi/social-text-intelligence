# Core Contracts

Milestone 2 defined stable application contracts. Milestones 3 and 4 use them for
real local sentiment, emotion, and combined single-text analysis.

## Normalized input

`NormalizedTextInput` converts platform-neutral text and metadata into an
immutable record. It normalizes Unicode and line endings, validates length and
language metadata, and rejects empty input. It does not detect language, store
records, or log text.

## Normalized results

Sentiment uses `positive`, `negative`, and `neutral`. Emotion uses the compact
taxonomy from the Project Charter: joy, amusement, admiration, gratitude, anger,
sadness, fear, disgust, and neutral.

Normalized application scores and model-native scores are separate. Every result
records provider name, model name, exact revision, task, supported languages, and
native labels. Neutral means no clear emotional expression; it is not presented
as a literal emotion or psychological conclusion.

Emotion results contain every compact score, all provider-native scores,
dominant emotion, confidence, inclusive threshold, and ordered secondary
emotions. Multi-label scores are independent and are not normalized to sum to
one. Neutral is selected only when no compact non-neutral score reaches the
threshold.

## Providers

`SentimentProvider` and `EmotionProvider` are runtime-checkable protocols. The
Cardiff sentiment provider implements `SentimentProvider` and maps the native
negative, neutral, and positive probabilities one-to-one. The Sam Lowe emotion
provider implements `EmotionProvider`, preserves 28 native probabilities, and
maps documented native groups into the nine compact labels.

The included deterministic providers exist only for unit and orchestration tests.
They return configured values, do not interpret text, and are not NLP models.

### Complete-input inference contract

`MAX_TEXT_LENGTH=20_000` is an application safety ceiling measured in
characters. It is not a proxy for model capacity. Cardiff sentiment and SamLowe
emotion each use an audited 512-token encoded-input budget. Providers call the
real tokenizer with special tokens enabled and truncation disabled, then reject
an encoded sequence above that budget with `model_input_too_long` before model
inference.

Combined analysis preflights every required provider before running either
model. A successful report therefore means every required pinned model consumed
the complete submitted text; no successful contract needs a `truncated` field.
An over-budget Direct or CLI request returns an explicit error explaining that
no truncation or partial analysis occurred. In Batch, only that row fails; its
exported model labels, scores, identities, and revisions remain blank. Automatic
chunking, cross-chunk aggregation, summarization, and long-form analysis are not
part of version 0.10.0.

## Batch CSV

The required logical field is `text`; the interface supports selecting another
column as the text source. Optional trusted fields are `record_id`, `source_type`,
`source_label`, `language`, `timestamp`, `topic`, `community`,
`parent_record_id`, and `notes`. Other columns are reported and ignored.

Missing IDs become deterministic `batch-row-NNNNNN` identities. Duplicate
supplied IDs are explicit `duplicate_record_id` row errors. Each input row yields
one `ok` or `error` outcome with a typed error code and message. File size, row
count, and per-text length limits are enforced before or during preview.

An optional `timestamp` must be ISO 8601 but is otherwise preserved exactly as
supplied: a stated UTC offset is kept as stated, and a value with no timezone
stays timezone-unspecified. The application never infers a timezone for such a
value and never normalizes user timestamps to UTC. This is deliberately
distinct from system-generated audit timestamps — review, moderation, triage,
context-note, and export times are always timezone-aware UTC.

Sentiment distribution counts mutually exclusive selected labels. Dominant
emotion distribution counts one selected compact label per successful row.
Compact activation rates independently count scores at or above each result's
threshold and therefore do not sum to 100 percent.

## Human review

Only outcomes with an `AnalysisReport` receive a `HumanReview`. Sentiment and
emotion judgments are independently `accept`, `correct`, or `uncertain`. A review
is whole-record complete only when both judgments exist. Accept copies the
corresponding compact AI labels, correct requires valid human labels, and
uncertain clears the human labels for that dimension. Human confidence scores are
not collected.

Corrected emotion review requires one dominant compact label and zero or more
unique secondary labels. The dominant label cannot repeat as secondary, neutral
cannot coexist with any non-neutral label, and secondaries are stored in compact
taxonomy order. Review notes are optional and bounded to 2,000 characters.
Completed timestamps are timezone-aware UTC ISO 8601 values.

Agreement is `true` or `false` only for a whole-record reviewed, definitive
dimension; it is blank for partial or uncertain review. Emotion-set agreement is
exact set equality across dominant plus secondary compact labels. Failures have
blank review fields but remain in reviewed export alongside their original error.

## Errors

Expected contract failures use typed exceptions:

- `ValidationError` for invalid input or scores;
- `UnsupportedLanguageError` for provider-language mismatches;
- `ModelInputTooLongError` (`model_input_too_long`) when a pinned model cannot
  consume the complete encoded input;
- `InvalidProviderOutputError` for results that violate normalized contracts;
- `ProviderError` as the base for provider failures.

The core performs no persistence, networking, telemetry, or full-text logging.

## Ephemeral workspace mutation integrity

Batch, Review, Insights, Moderation, and Triage business mutations are derived
from the current workspace while the process-memory store lock is held. Routes
do not commit whole workspaces derived from an earlier `get()`. Independent
changes to different records, notes, cases, sessions, or tickets are retained.

One-shot transitions are revalidated against commit-time state. A competing
first moderation decision, stale Batch column selection, or repeated Triage
finalize cannot silently replace the accepted mutation; the incompatible request
receives HTTP 409. Explicit revision workflows remain valid and retain their
existing first/final provenance. Missing, expired, or cleared workspaces retain
their existing 404 behavior.

Rendering, filters, navigation, summaries, and exports are read-only transient
operations and need no mutation transaction. Insight selection remains a
lightweight remembered UI selection, but its atomic update preserves the latest
notes. Creates and explicit clears already execute as single locked store
operations. Batch analysis continues to use its stronger exclusive lease and
lease-identity write-back contract.

## Local browser boundary

The Flask CLI binds to `127.0.0.1`. HTTP Host validation accepts only
`127.0.0.1` and `localhost`; a port does not change Host trust. Any other Host
returns a fixed HTTP 400 before route dispatch, inference, or state mutation.

For `POST`, `PUT`, `PATCH`, and `DELETE`, an explicit Origin must exactly match
the request scheme, host, and effective port. `null`, malformed, and external
origins return a fixed HTTP 403. If Origin is absent but Referer is present, the
Referer origin must match by the same rule. If both are absent, the request is
accepted as a local non-browser client and still requires a trusted Host. This
lightweight boundary creates no account, cookie session, CSRF token, CORS, or
remote-access contract.

All responses carry:

- `Content-Security-Policy: default-src 'self'; base-uri 'none'; connect-src
  'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src
  'self'; object-src 'none'; script-src 'self'; style-src 'self'`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: same-origin`;
- `X-Frame-Options: DENY`;
- the existing no-store/no-cache headers.

The policy permits only checked-in local CSS and JavaScript. It contains no
wildcard, external CDN, `unsafe-inline`, or reporting endpoint. HSTS is excluded
because the local product intentionally serves loopback HTTP, and CORS is not
enabled. Host rejection is 400, origin/referer rejection is 403, request-body
rejection remains 413, mutation conflict remains 409, and expired state remains
404.

## Insights and context notes

Insight grouping accepts only `source_type`, `source_label`, `topic`,
`community`, `language`, and a month derived from a valid normalized timestamp.
Group membership is never inferred from record text or model output. An
`InsightSelection` binds one grouping, one or more exact group values, one
perspective, one compatible metric, and optional existing AI-label/date filters.

Timestamp-month grouping and the result-date filters read the date each record
itself states, without converting it to UTC or to any other zone. A record that
states an offset is therefore grouped by its own local calendar date, not by
its UTC date. This keeps grouping faithful to the supplied value instead of
substituting an inferred one.

AI distributions use successful rows. Human distributions use only
whole-record reviewed, definitive dimensions. Disagreement uses the same
definitive eligibility and means descriptive AI-human disagreement, not
accuracy. Each value carries a raw count and denominator. The sample-size policy
is applied separately to every group and metric: fewer than five is insufficient
for comparison, five through nine is a small sample, and ten or more permits
ordinary descriptive comparison.

Group-level audit context counts successful and failed input rows separately.
A failed row is assigned only when its selected grouping can be read reliably
from the normalized record or independently validated from the supported
user-provided metadata. Simple text metadata must be within its contract limit,
`source_type` and `language` must be valid, and timestamp grouping requires a
parseable timestamp month. Otherwise the failed row is explicitly unassigned;
the application never infers a group from text or another field. Because failed
rows have no AI result, AI-label and result-date filters do not apply to their
group-context counts.

`ContextNote` is a separate user-authored annotation associated with a record,
trusted metadata value, or comparison description. Its phrase, explanation,
context-importance text, and allowlisted tags do not modify model scores,
reviews, or agreement. Every note records a timezone-aware UTC creation time;
there is no edit history or persistence. `RepresentativeExample` contains an
existing outcome, its separate review when present, and the deterministic reason
it was selected.

Insight CSV export begins with an audit row containing timezone-aware UTC export
time, the exact metric definition, configured sample thresholds, input/analysis
counts, review coverage counts, active filters and selection, model provenance,
and inclusive per-row emotion-threshold semantics. Group rows retain raw counts,
denominators, rates, sample warnings, successful/failed group counts, and the
failed-row unassigned count. Context-note rows include their UTC creation time.

## Moderation training

`ModerationJudgment` records disposition, primary and secondary categories,
severity, escalation, and any required escalation or unclear reasons.
`TraineeDecision` adds required reasoning, required reviewer note, and the exact
non-blocking guidance warnings produced for that judgment.

Structural validation rejects incomplete or contradictory data. `No violation`
is exclusive, a primary category cannot repeat as secondary, Warn and Remove
require a primary violation, escalation requires a reason, Unclear / Needs
Review requires an unclear reason, and enumerations must be supported.
`guidance_warnings()` separately identifies combinations that depart from the
ordinary synthetic-policy default. These warnings do not block submission or
alter a decision.

`ReferenceDecision` stores one preferred complete judgment, zero or more
distinct complete acceptable alternatives, a rationale, frozen policy clause
IDs, and provenance. `built_in` identifies repository synthetic fixtures;
`self_authored` identifies a reference created and trained against by the same
local user. `user_authored` remains reserved for a future external author or
policy-provider workflow and is not exposed as an M9 authoring choice.

`ModerationTrainingSession` freezes cases, policy versions, references, clause
IDs, mode, feedback timing, and order. `CaseAttempt` preserves an immutable
first decision plus a separately timestamped final revision. Exact preferred,
complete acceptable alternative, disagreement, and unscored states remain
distinct. Summaries retain raw numerators, denominators, exclusions, and sample
warnings; no composite score is defined.

## Support triage

`TriageFields` keeps primary and secondary intents, one issue category, urgency,
recommended queue, escalation, primary and secondary recommended next actions,
unclear explanation, and human notes separate. A saved draft may omit required
final fields but cannot contain unsupported enum values, duplicates, excessive
secondary selections, primary/secondary repetition, invalid lengths, or
conflicting escalation fields.

`validate_final_fields()` requires all primary fields and conditional
explanations. Escalation requires one supported reason. Other/Unclear category
or Unclear urgency requires an explanation. Escalation, guide warnings, unclear
classifications, and consequential visible-mock overrides require human notes.
`triage_guidance_warnings()` separately retains unusual synthetic-guide
departures without rewriting or blocking the human decision.

`SupportTicket` has stable source provenance, complexity, guide identity,
applicable rule IDs, optional deterministic mock provenance, and an optional
workspace snapshot. Workspace snapshots contain literal source text or a literal
bounded excerpt plus separately stored trusted metadata, NLP signals, human
review, and context notes. Parsed rows are eligible even when analysis failed.

`TicketTriageState` is limited to Untriaged, Draft, and Finalized. The first
finalized decision and its guide provenance are immutable. A revision replaces
only the current final decision and increments a revision count.
`MockTriageSuggestion` is either `built_in_mock` or `self_authored_mock`;
unavailable is explicit. Core human–mock comparisons cover intent, category,
urgency, recommended queue, escalation, and primary next action. They define
descriptive agreement and overrides, never accuracy or quality.

### Timestamp sort ordering

Workspace sorting by timestamp reads the record timestamp captured in the
frozen snapshot and never rewrites, converts, or normalizes the stored value.
Ordering is deterministic and separates timestamps that state an offset from
timestamps that do not:

1. Records whose timestamp states a UTC offset sort first, ascending by real
   instant rather than by the raw ISO text. Two different offsets that denote
   the same instant compare equal.
2. Records whose timestamp states no timezone sort next, in a separate bucket
   ordered by their stated wall-clock value. They are never assigned UTC, a
   local zone, or any geographic zone, and are never merged into the
   offset-aware timeline. A date-only value keeps its existing parsed meaning.
3. Records with a missing or unusable timestamp sort last.

Every tie inside a bucket falls back to the original workspace order, so the
sort is stable, and values from different buckets are never compared with each
other. Because timestamps that state no timezone cannot be placed on a shared
real timeline, the interface presents the three groups as an explicit ordering
rule and does not imply that they share one.
