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

## Batch CSV

The required logical field is `text`; the interface supports selecting another
column as the text source. Optional trusted fields are `record_id`, `source_type`,
`source_label`, `language`, `timestamp`, `topic`, `community`,
`parent_record_id`, and `notes`. Other columns are reported and ignored.

Missing IDs become deterministic `batch-row-NNNNNN` identities. Duplicate
supplied IDs are explicit `duplicate_record_id` row errors. Each input row yields
one `ok` or `error` outcome with a typed error code and message. File size, row
count, and per-text length limits are enforced before or during preview.

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
- `InvalidProviderOutputError` for results that violate normalized contracts;
- `ProviderError` as the base for provider failures.

The core performs no persistence, networking, telemetry, or full-text logging.
