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

## Errors

Expected contract failures use typed exceptions:

- `ValidationError` for invalid input or scores;
- `UnsupportedLanguageError` for provider-language mismatches;
- `InvalidProviderOutputError` for results that violate normalized contracts;
- `ProviderError` as the base for provider failures.

The core performs no persistence, networking, telemetry, or full-text logging.
