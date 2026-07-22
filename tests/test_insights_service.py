"""Milestone 8 insight metrics, notes, examples, and export tests."""

import csv
import io
import unittest
from datetime import UTC, datetime

from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
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
from social_text_intelligence.services.insights import (
    ContextTag,
    ExampleMode,
    GroupingDimension,
    InsightMetric,
    InsightPerspective,
    InsightSelection,
    InsightState,
    SampleSizeLevel,
    add_context_note,
    available_group_values,
    build_group_metrics,
    delete_context_note,
    export_insights_csv,
    parse_insight_filters,
    sample_size_assessment,
    select_representative_examples,
)
from social_text_intelligence.services.review import (
    ReviewState,
    accept_both,
    create_review_state,
    update_review,
)


def result() -> BatchResult:
    rows = ["record_id,text,topic,community,timestamp"]
    for number in range(1, 13):
        topic = "release" if number <= 6 else "support"
        community = "group-a" if number % 2 else "group-b"
        rows.append(
            f"row-{number},Synthetic row {number}.,{topic},{community},"
            f"2026-07-{number:02d}T12:00:00+00:00"
        )
    content = ("\n".join(rows) + "\n").encode()
    preview = prepare_csv_batch(
        PendingBatchUpload(
            content=content,
            headers=("record_id", "text", "topic", "community", "timestamp"),
        ),
        text_column="text",
        max_rows=20,
        max_text_length=100,
    )
    return analyze_batch(
        preview,
        AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        ),
    )


def reviewed_state(batch: BatchResult) -> ReviewState:
    state = create_review_state(batch)
    for number in range(1, 6):
        state = accept_both(
            batch,
            state,
            record_id=f"row-{number}",
            note="",
            now=lambda: datetime(2026, 7, 22, tzinfo=UTC),
        )
    return update_review(
        batch,
        state,
        record_id="row-6",
        sentiment_judgment="correct",
        human_sentiment="negative",
        emotion_judgment="uncertain",
        human_dominant_emotion=None,
        human_secondary_emotions=(),
        note="Synthetic uncertainty.",
        now=lambda: datetime(2026, 7, 22, tzinfo=UTC),
    )


class SelectiveFailureAnalyzer:
    def __init__(self) -> None:
        self.delegate = AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        if "analysis failure" in record.text:
            raise RuntimeError("synthetic provider failure")
        return self.delegate.analyze(record)


class InsightServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = result()
        self.reviews = reviewed_state(self.result)

    def selection(
        self,
        metric: InsightMetric,
        perspective: InsightPerspective,
        groups: tuple[str, ...] = ("release", "support"),
    ) -> InsightSelection:
        return InsightSelection(
            grouping=GroupingDimension.TOPIC,
            groups=groups,
            perspective=perspective,
            metric=metric,
        )

    def test_only_trusted_group_values_and_valid_dates_are_used(self) -> None:
        self.assertEqual(
            available_group_values(self.result, GroupingDimension.TOPIC),
            ("release", "support"),
        )
        self.assertEqual(
            available_group_values(
                self.result, GroupingDimension.TIMESTAMP_MONTH
            ),
            ("2026-07",),
        )
        with self.assertRaisesRegex(ValidationError, "YYYY-MM-DD"):
            parse_insight_filters(date_from="July 1")

        filtered = InsightSelection(
            grouping=GroupingDimension.TOPIC,
            groups=("release",),
            perspective=InsightPerspective.AI,
            metric=InsightMetric.AI_SENTIMENT,
            filters=parse_insight_filters(
                date_from="2026-07-03", date_to="2026-07-04"
            ),
        )
        summary = build_group_metrics(self.result, self.reviews, filtered)[0]
        self.assertEqual(summary.eligible_count, 2)
        self.assertEqual(summary.sample.level, SampleSizeLevel.INSUFFICIENT)

    def test_ai_metrics_use_successful_rows_and_independent_activation(self) -> None:
        summaries = build_group_metrics(
            self.result,
            self.reviews,
            self.selection(
                InsightMetric.AI_EMOTION_ACTIVATION,
                InsightPerspective.AI,
            ),
            comparison=True,
        )
        release = summaries[0]
        self.assertEqual(release.total_count, 6)
        self.assertEqual(release.eligible_count, 6)
        values = {value.label: value for value in release.values}
        self.assertEqual(values["gratitude"].count, 6)
        self.assertEqual(values["joy"].count, 6)
        self.assertEqual(values["gratitude"].denominator, 6)

    def test_group_context_counts_successes_failures_and_unassigned_rows(self) -> None:
        content = (
            b"record_id,text,topic,timestamp\n"
            b"ok,Synthetic success.,release,2026-07-01T12:00:00+00:00\n"
            b"provider-fail,Synthetic analysis failure.,release,"
            b"2026-07-02T12:00:00+00:00\n"
            b"invalid-text,,support,2026-07-03T12:00:00+00:00\n"
            b"invalid-time,,support,not-a-timestamp\n"
        )
        preview = prepare_csv_batch(
            PendingBatchUpload(
                content=content,
                headers=("record_id", "text", "topic", "timestamp"),
            ),
            text_column="text",
            max_rows=10,
            max_text_length=100,
        )
        batch = analyze_batch(preview, SelectiveFailureAnalyzer())
        reviews = create_review_state(batch)
        topic = build_group_metrics(
            batch,
            reviews,
            InsightSelection(
                GroupingDimension.TOPIC,
                ("release", "support"),
                InsightPerspective.AI,
                InsightMetric.AI_SENTIMENT,
            ),
        )
        self.assertEqual(
            (topic[0].successful_count, topic[0].failed_count), (1, 1)
        )
        self.assertEqual(
            (topic[1].successful_count, topic[1].failed_count), (0, 2)
        )
        exported = export_insights_csv(
            batch,
            reviews,
            InsightState(),
            InsightSelection(
                GroupingDimension.TOPIC,
                ("release", "support"),
                InsightPerspective.AI,
                InsightMetric.AI_SENTIMENT,
            ),
            include_records=False,
            include_native=False,
            now=lambda: datetime(2026, 7, 22, tzinfo=UTC),
        )
        export_rows = list(csv.DictReader(io.StringIO(exported)))
        group_rows = {
            row["group"]: row
            for row in export_rows
            if row["section"] == "group_summary" and row["label"] == "positive"
        }
        self.assertEqual(
            group_rows["release"]["group_successful_analysis_count"], "1"
        )
        self.assertEqual(group_rows["release"]["group_failed_count"], "1")
        self.assertEqual(
            group_rows["support"]["group_successful_analysis_count"], "0"
        )
        self.assertEqual(group_rows["support"]["group_failed_count"], "2")

        month = build_group_metrics(
            batch,
            reviews,
            InsightSelection(
                GroupingDimension.TIMESTAMP_MONTH,
                ("2026-07",),
                InsightPerspective.AI,
                InsightMetric.AI_SENTIMENT,
            ),
        )[0]
        self.assertEqual(month.total_count, 3)
        self.assertEqual(month.failed_count, 2)
        self.assertEqual(month.unassigned_failed_count, 1)

    def test_human_and_disagreement_denominators_exclude_uncertain(self) -> None:
        human = build_group_metrics(
            self.result,
            self.reviews,
            self.selection(
                InsightMetric.HUMAN_SENTIMENT,
                InsightPerspective.HUMAN,
                ("release",),
            ),
        )[0]
        self.assertEqual(human.eligible_count, 6)
        self.assertEqual(
            {value.label: value.count for value in human.values},
            {"positive": 5, "negative": 1, "neutral": 0},
        )

        emotion = build_group_metrics(
            self.result,
            self.reviews,
            self.selection(
                InsightMetric.DOMINANT_EMOTION_DISAGREEMENT,
                InsightPerspective.AGREEMENT,
                ("release",),
            ),
        )[0]
        self.assertEqual(emotion.eligible_count, 5)
        self.assertEqual(emotion.uncertain_count, 1)
        self.assertEqual(emotion.values[0].denominator, 5)

    def test_sample_size_policy_applies_per_metric_group(self) -> None:
        self.assertEqual(
            sample_size_assessment(4).level, SampleSizeLevel.INSUFFICIENT
        )
        self.assertFalse(sample_size_assessment(4).emphasize_percentages)
        self.assertEqual(sample_size_assessment(5).level, SampleSizeLevel.SMALL)
        self.assertFalse(sample_size_assessment(9).allow_comparison)
        self.assertTrue(sample_size_assessment(10).allow_comparison)

    def test_comparison_requires_two_to_four_known_groups(self) -> None:
        with self.assertRaisesRegex(ValidationError, "two and four"):
            build_group_metrics(
                self.result,
                self.reviews,
                self.selection(
                    InsightMetric.AI_SENTIMENT,
                    InsightPerspective.AI,
                    ("release",),
                ),
                comparison=True,
            )
        with self.assertRaisesRegex(ValidationError, "not present"):
            build_group_metrics(
                self.result,
                self.reviews,
                self.selection(
                    InsightMetric.AI_SENTIMENT,
                    InsightPerspective.AI,
                    ("missing",),
                ),
            )

    def test_context_notes_are_separate_validated_and_deletable(self) -> None:
        created_at = datetime(2026, 7, 22, 15, 30, tzinfo=UTC)
        state = add_context_note(
            InsightState(),
            self.result,
            association="record",
            association_value="row-1",
            phrase="Synthetic phrase",
            explanation="The phrase is quoted.",
            context_importance="Quotation changes the reading.",
            tags=(ContextTag.QUOTATION_OR_REPORTED_SPEECH,),
            now=lambda: created_at,
        )
        self.assertEqual(len(state.notes), 1)
        self.assertEqual(state.notes[0].created_at, created_at)
        first_review = self.reviews.for_record("row-1")
        assert first_review is not None
        self.assertIsNone(first_review.note)
        state = delete_context_note(state, note_id=state.notes[0].note_id)
        self.assertEqual(state.notes, ())
        with self.assertRaisesRegex(ValidationError, "not present"):
            add_context_note(
                state,
                self.result,
                association="record",
                association_value="unknown",
                phrase="Synthetic phrase",
                explanation="Synthetic explanation.",
                context_importance="Synthetic context.",
                tags=(),
            )
        with self.assertRaisesRegex(ValidationError, "exceeds"):
            add_context_note(
                state,
                self.result,
                association="record",
                association_value="row-1",
                phrase="x" * 501,
                explanation="Synthetic explanation.",
                context_importance="Synthetic context.",
                tags=(),
            )

    def test_examples_state_selection_reason_and_export_formula_safety(self) -> None:
        notes = add_context_note(
            InsightState(),
            self.result,
            association="record",
            association_value="row-1",
            phrase="=synthetic phrase",
            explanation="@synthetic explanation",
            context_importance="+synthetic context",
            tags=(ContextTag.OTHER,),
        )
        examples = select_representative_examples(
            self.result,
            self.reviews,
            notes,
            mode=ExampleMode.CONTEXT_NOTES,
        )
        self.assertEqual(examples[0].outcome.prepared.identity, "row-1")
        self.assertIn("user-authored", examples[0].reason)
        tagged_examples = select_representative_examples(
            self.result,
            self.reviews,
            notes,
            mode=ExampleMode.CONTEXT_NOTES,
            context_tag=ContextTag.OTHER,
        )
        self.assertEqual(len(tagged_examples), 1)
        self.assertIn("tagged other", tagged_examples[0].reason)

        exported = export_insights_csv(
            self.result,
            self.reviews,
            notes,
            self.selection(
                InsightMetric.AI_SENTIMENT,
                InsightPerspective.AI,
                ("release",),
            ),
            include_records=True,
            include_native=False,
            now=lambda: datetime(2026, 7, 22, 16, 45, tzinfo=UTC),
        )
        rows = list(csv.DictReader(io.StringIO(exported)))
        metadata = rows[0]
        self.assertEqual(metadata["section"], "export_metadata")
        self.assertEqual(metadata["exported_at"], "2026-07-22T16:45:00+00:00")
        self.assertIn("successful row", metadata["metric_definition"])
        self.assertEqual(metadata["insufficient_sample_below"], "5")
        self.assertEqual(metadata["small_sample_below"], "10")
        self.assertEqual(metadata["total_input_count"], "12")
        self.assertEqual(metadata["successful_analysis_count"], "12")
        self.assertEqual(metadata["failed_count"], "0")
        self.assertEqual(metadata["reviewable_count"], "12")
        self.assertEqual(metadata["whole_record_reviewed_count"], "6")
        self.assertEqual(metadata["definitive_sentiment_review_count"], "6")
        self.assertEqual(metadata["definitive_emotion_review_count"], "5")
        self.assertEqual(metadata["uncertain_count"], "1")
        self.assertEqual(metadata["unreviewed_count"], "6")
        note_row = next(row for row in rows if row["section"] == "context_note")
        self.assertEqual(note_row["phrase"], "'=synthetic phrase")
        self.assertEqual(note_row["explanation"], "'@synthetic explanation")
        self.assertEqual(note_row["context_importance"], "'+synthetic context")
        self.assertRegex(note_row["created_at"], r"\+00:00$")
        record_rows = [
            row for row in rows if row["section"] == "supporting_record"
        ]
        self.assertEqual(len(record_rows), 6)
        self.assertTrue(
            all(not row["native_emotion_scores"] for row in record_rows)
        )

    def test_metric_must_match_perspective(self) -> None:
        with self.assertRaisesRegex(ValidationError, "perspective"):
            self.selection(
                InsightMetric.HUMAN_SENTIMENT,
                InsightPerspective.AI,
            )


if __name__ == "__main__":
    unittest.main()
