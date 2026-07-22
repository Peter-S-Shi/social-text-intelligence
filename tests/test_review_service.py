"""Human-review validation, state, filtering, and navigation tests."""

import unittest
from datetime import UTC, datetime

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.contracts.errors import ValidationError
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService
from social_text_intelligence.services.batch import (
    BatchResult,
    PendingBatchUpload,
    analyze_batch,
    prepare_csv_batch,
)
from social_text_intelligence.services.review import (
    accept_both,
    create_review_state,
    filter_review_cases,
    review_navigation,
    update_review,
)


def fixed_now() -> datetime:
    return datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


def result() -> BatchResult:
    preview = prepare_csv_batch(
        PendingBatchUpload(
            content=(
                b"record_id,text\n"
                b"first,Synthetic positive row.\n"
                b"failed,\n"
                b"third,Synthetic mixed row.\n"
            ),
            headers=("record_id", "text"),
        ),
        text_column="text",
        max_rows=10,
        max_text_length=100,
    )
    analyzer = AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(SentimentLabel.POSITIVE),
        emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
    )
    return analyze_batch(preview, analyzer)


class ReviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = result()
        self.state = create_review_state(self.result)

    def test_failed_rows_do_not_enter_review_state(self) -> None:
        self.assertEqual(
            tuple(review.record_id for review in self.state.reviews),
            ("first", "third"),
        )

    def test_partial_review_remains_unreviewed_and_keeps_ai_immutable(self) -> None:
        original_report = self.result.outcomes[0].report
        updated = update_review(
            self.result,
            self.state,
            record_id="first",
            sentiment_judgment="accept",
            human_sentiment="negative",
            emotion_judgment=None,
            human_dominant_emotion=None,
            human_secondary_emotions=(),
            note="  Synthetic note.  ",
            now=fixed_now,
        )
        review = updated.for_record("first")
        assert review is not None
        self.assertFalse(review.is_reviewed)
        self.assertEqual(review.human_sentiment, SentimentLabel.POSITIVE)
        self.assertIsNone(review.reviewed_at)
        self.assertEqual(review.note, "Synthetic note.")
        self.assertIs(self.result.outcomes[0].report, original_report)

    def test_accept_both_copies_ai_labels_and_sets_utc_timestamp(self) -> None:
        updated = accept_both(
            self.result,
            self.state,
            record_id="first",
            note="",
            now=fixed_now,
        )
        review = updated.for_record("first")
        assert review is not None
        self.assertTrue(review.is_reviewed)
        self.assertEqual(review.human_sentiment, SentimentLabel.POSITIVE)
        self.assertEqual(review.human_dominant_emotion, EmotionLabel.GRATITUDE)
        self.assertEqual(review.human_secondary_emotions, (EmotionLabel.JOY,))
        self.assertEqual(review.reviewed_at, fixed_now())

    def test_corrections_require_labels_and_enforce_neutral_exclusivity(self) -> None:
        with self.assertRaisesRegex(ValidationError, "human sentiment"):
            update_review(
                self.result,
                self.state,
                record_id="first",
                sentiment_judgment="correct",
                human_sentiment=None,
                emotion_judgment="accept",
                human_dominant_emotion=None,
                human_secondary_emotions=(),
                note="",
            )
        with self.assertRaisesRegex(ValidationError, "Neutral"):
            update_review(
                self.result,
                self.state,
                record_id="first",
                sentiment_judgment="accept",
                human_sentiment=None,
                emotion_judgment="correct",
                human_dominant_emotion="neutral",
                human_secondary_emotions=("joy",),
                note="",
            )

    def test_corrected_emotions_use_stable_taxonomy_order(self) -> None:
        updated = update_review(
            self.result,
            self.state,
            record_id="first",
            sentiment_judgment="correct",
            human_sentiment="negative",
            emotion_judgment="correct",
            human_dominant_emotion="anger",
            human_secondary_emotions=("disgust", "fear"),
            note="",
            now=fixed_now,
        )
        review = updated.for_record("first")
        assert review is not None
        self.assertEqual(
            review.human_secondary_emotions,
            (EmotionLabel.FEAR, EmotionLabel.DISGUST),
        )

    def test_uncertain_clears_human_labels(self) -> None:
        updated = update_review(
            self.result,
            self.state,
            record_id="first",
            sentiment_judgment="uncertain",
            human_sentiment="positive",
            emotion_judgment="uncertain",
            human_dominant_emotion="joy",
            human_secondary_emotions=("gratitude",),
            note="Not enough context.",
            now=fixed_now,
        )
        review = updated.for_record("first")
        assert review is not None
        self.assertIsNone(review.human_sentiment)
        self.assertIsNone(review.human_dominant_emotion)
        self.assertEqual(review.human_secondary_emotions, ())

    def test_filters_and_navigation_use_record_level_semantics(self) -> None:
        updated = accept_both(
            self.result,
            self.state,
            record_id="first",
            note="",
            now=fixed_now,
        )
        reviewed = filter_review_cases(
            self.result, updated, review_filter="reviewed"
        )
        unreviewed = filter_review_cases(
            self.result, updated, review_filter="unreviewed"
        )
        self.assertEqual([case.review.record_id for case in reviewed], ["first"])
        self.assertEqual([case.review.record_id for case in unreviewed], ["third"])
        navigation = review_navigation(
            self.result,
            updated,
            current_record_id="first",
            filtered_cases=filter_review_cases(self.result, updated),
        )
        self.assertIsNone(navigation.previous_row)
        self.assertEqual(navigation.next_row, 3)
        self.assertEqual(navigation.next_unreviewed_row, 3)

    def test_non_reviewable_record_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "successfully analyzed"):
            accept_both(
                self.result,
                self.state,
                record_id="failed",
                note="",
            )


if __name__ == "__main__":
    unittest.main()
