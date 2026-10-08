"""The insights workflow over a real SQLite project (synthetic data)."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from pathlib import Path

import pytest

from social_text_intelligence.application.insights_workflow import (
    ExampleControls,
    ExampleMode,
    GroupingDimension,
    InsightControls,
    InsightMetric,
    InsightPerspective,
    InsightsUnavailableError,
    InsightsWorkflow,
    NoteDraft,
    SampleSizeLevel,
)
from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectNotFoundError,
    ProjectWorkflow,
)
from social_text_intelligence.application.projects import BatchWorkspace
from social_text_intelligence.application.review_workflow import (
    ReviewDraft,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.contracts.errors import ValidationError
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.insights import ContextAssociation, ContextTag

from .insight_samples import SENTINEL, VariedGateway, insights_csv

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)
CORRECT, ACCEPT, UNCERTAIN = (
    ReviewJudgment.CORRECT,
    ReviewJudgment.ACCEPT,
    ReviewJudgment.UNCERTAIN,
)


def repository(root: Path) -> SqliteProjectRepository:
    return SqliteProjectRepository(AppDataLocations(root))


def insights(root: Path) -> InsightsWorkflow:
    """A fresh workflow, as after an application restart."""

    return InsightsWorkflow(repository(root))


def analysed(root: Path) -> str:
    flow = ProjectWorkflow(repository(root), VariedGateway(), LIMITS)
    project_id = flow.import_csv(insights_csv(), name="P").summary.project_id
    flow.analyze(project_id)
    return project_id


def review(root: Path, project_id: str, row: int, draft: ReviewDraft) -> None:
    flow = ReviewWorkflow(repository(root))
    seen = flow.open_review(project_id, row=row).record
    assert seen is not None
    flow.save(project_id, row, draft, expected=seen.review)


def accept_both(root: Path, project_id: str, row: int) -> None:
    flow = ReviewWorkflow(repository(root))
    seen = flow.open_review(project_id, row=row).record
    assert seen is not None
    flow.accept_both(project_id, row, "", expected=seen.review)


def controls(**changes: object) -> InsightControls:
    base = {
        "grouping": GroupingDimension.TOPIC,
        "groups": ("shipping",),
        "perspective": InsightPerspective.AI,
        "metric": InsightMetric.AI_SENTIMENT,
    }
    return InsightControls(**{**base, **changes})  # type: ignore[arg-type]


def counts(summary: object) -> dict[str, tuple[int, int]]:
    return {v.label: (v.count, v.denominator) for v in summary.values}  # type: ignore[attr-defined]


# -- AI perspective, groups, counts -------------------------------------------


def test_opening_uses_the_default_view_and_the_service_counts(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).open_insights(project_id)

    selection = snapshot.selection
    assert selection.grouping is GroupingDimension.TOPIC
    assert selection.perspective is InsightPerspective.AI
    assert selection.groups == ("billing",)  # the first group, as the web UI does
    (billing,) = snapshot.summaries
    assert (billing.total_count, billing.successful_count, billing.failed_count) == (
        8,
        7,
        1,
    )
    assert counts(billing)["negative"] == (3, 7)
    assert counts(billing)["neutral"] == (4, 7)
    assert counts(billing)["positive"] == (0, 7)
    assert billing.sample.level is SampleSizeLevel.SMALL
    assert billing.sample.message == "Small sample"
    assert snapshot.groups_for(GroupingDimension.TOPIC) == (
        "billing",
        "returns",
        "shipping",
        "(not supplied)",
    )


def test_a_larger_group_has_no_warning_and_a_tiny_one_is_insufficient(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).apply(
        project_id, controls(groups=("shipping", "returns"), comparison=True)
    )

    shipping, returns = snapshot.summaries
    assert shipping.sample.level is SampleSizeLevel.DESCRIPTIVE
    assert shipping.sample.message is None
    assert counts(shipping)["positive"] == (4, 12)
    assert returns.sample.level is SampleSizeLevel.INSUFFICIENT
    assert returns.sample.message == "Insufficient sample for comparison"
    assert returns.sample.allow_comparison is False
    assert returns.sample.emphasize_percentages is False


def test_failed_rows_follow_the_service_grouping_rules(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)

    by_topic = flow.apply(project_id, controls(groups=("shipping", "billing")))
    by_month = flow.apply(
        project_id,
        controls(
            grouping=GroupingDimension.TIMESTAMP_MONTH, groups=("2026-01", "2026-02")
        ),
    )

    shipping, billing = by_topic.summaries
    assert shipping.failed_count == 1  # the gateway failure keeps its topic
    assert billing.failed_count == 1  # so does the row with a bad timestamp
    assert shipping.unassigned_failed_count == 0
    january, february = by_month.summaries
    # the bad-timestamp row cannot be placed in a month: it stays unassigned
    assert january.unassigned_failed_count == 1
    assert january.failed_count == 1  # the gateway failure is dated 2026-01-20
    assert february.failed_count == 0


def test_missing_metadata_is_its_own_visible_group(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).apply(
        project_id, controls(groups=("(not supplied)",))
    )

    (missing,) = snapshot.summaries
    assert (missing.group, missing.total_count, missing.successful_count) == (
        "(not supplied)",
        2,
        2,
    )


def test_language_grouping_uses_only_the_supplied_metadata(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).apply(
        project_id,
        controls(grouping=GroupingDimension.LANGUAGE, groups=("en",)),
    )

    assert snapshot.groups_for(GroupingDimension.LANGUAGE) == ("en",)
    assert snapshot.selection.grouping is GroupingDimension.LANGUAGE


def test_filters_narrow_the_eligible_rows(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)

    negative = flow.apply(
        project_id, controls(groups=("shipping",), sentiment=SentimentLabel.NEGATIVE)
    )
    dated = flow.apply(
        project_id, controls(groups=("shipping",), date_from="2026-02-01")
    )

    (shipping,) = negative.summaries
    assert shipping.filtered_successful_count == 4  # r5-r8
    assert counts(shipping)["negative"] == (4, 4)
    (late,) = dated.summaries
    assert late.filtered_successful_count == 6  # r7-r12 are in February


def test_a_bad_filter_is_refused_and_does_not_replace_the_saved_view(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.apply(project_id, controls(groups=("shipping",)))

    with pytest.raises(ValidationError) as failure:
        flow.apply(project_id, controls(groups=("billing",), date_from="01/02/2026"))

    assert failure.value.code == "invalid_date"
    assert insights(tmp_path).open_insights(project_id).selection.groups == (
        "shipping",
    )


# -- human and agreement perspectives -----------------------------------------


def test_human_metrics_use_only_definitive_reviews(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    accept_both(tmp_path, project_id, 1)  # AI positive/joy accepted
    review(
        tmp_path,
        project_id,
        5,
        ReviewDraft(
            sentiment_judgment=CORRECT,
            human_sentiment=SentimentLabel.POSITIVE,
            emotion_judgment=CORRECT,
            human_dominant_emotion=EmotionLabel.JOY,
        ),
    )
    review(
        tmp_path,
        project_id,
        6,
        ReviewDraft(sentiment_judgment=UNCERTAIN, emotion_judgment=UNCERTAIN),
    )

    snapshot = insights(tmp_path).apply(
        project_id,
        controls(
            perspective=InsightPerspective.HUMAN,
            metric=InsightMetric.HUMAN_SENTIMENT,
        ),
    )

    (shipping,) = snapshot.summaries
    assert counts(shipping)["positive"] == (2, 2)  # r1 accepted, r5 corrected
    assert shipping.eligible_count == 2  # the uncertain r6 is not definitive
    assert shipping.uncertain_count == 1
    assert shipping.unreviewed_count == 9  # 12 rows, 3 reviewed
    assert shipping.sample.level is SampleSizeLevel.INSUFFICIENT


def test_agreement_is_descriptive_disagreement_among_definitive_reviews(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    accept_both(tmp_path, project_id, 1)  # agrees
    review(
        tmp_path,
        project_id,
        5,
        ReviewDraft(
            sentiment_judgment=CORRECT,
            human_sentiment=SentimentLabel.POSITIVE,
            emotion_judgment=CORRECT,
            human_dominant_emotion=EmotionLabel.JOY,
        ),
    )

    snapshot = insights(tmp_path).apply(
        project_id,
        controls(
            perspective=InsightPerspective.AGREEMENT,
            metric=InsightMetric.SENTIMENT_DISAGREEMENT,
        ),
    )

    (shipping,) = snapshot.summaries
    assert counts(shipping) == {"disagreement": (1, 2), "agreement": (1, 2)}
    assert "not model accuracy" in snapshot.metric_definition


def test_a_metric_from_another_perspective_is_refused(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    with pytest.raises(ValidationError) as failure:
        insights(tmp_path).apply(
            project_id,
            controls(
                perspective=InsightPerspective.HUMAN,
                metric=InsightMetric.AI_SENTIMENT,
            ),
        )

    assert failure.value.code == "incompatible_metric"


# -- comparison -------------------------------------------------------------


def test_a_comparison_of_one_group_is_refused_and_not_saved(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.apply(project_id, controls(groups=("billing",)))

    with pytest.raises(ValidationError) as failure:
        flow.apply(project_id, controls(groups=("shipping",), comparison=True))

    assert failure.value.code == "comparison_group_count"
    assert flow.open_insights(project_id).selection.groups == ("billing",)


def test_a_group_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    with pytest.raises(ValidationError) as failure:
        insights(tmp_path).apply(project_id, controls(groups=("shipping", "nope")))

    assert failure.value.code == "unknown_group"


def test_a_valid_comparison_shows_every_chosen_group(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).apply(
        project_id,
        controls(groups=("billing", "returns", "shipping"), comparison=True),
    )

    assert [s.group for s in snapshot.summaries] == ["billing", "returns", "shipping"]
    assert snapshot.comparison is True
    assert snapshot.error_message is None


# -- persistence --------------------------------------------------------------


def test_the_applied_selection_survives_a_fresh_app_instance(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    insights(tmp_path).apply(
        project_id,
        controls(
            groups=("shipping",),
            perspective=InsightPerspective.AI,
            metric=InsightMetric.AI_DOMINANT_EMOTION,
            emotion=EmotionLabel.ANGER,
            date_to="2026-03-01",
        ),
    )

    again = insights(tmp_path).open_insights(project_id)

    assert again.selection.groups == ("shipping",)
    assert again.selection.metric is InsightMetric.AI_DOMINANT_EMOTION
    assert again.selection.filters.emotion is EmotionLabel.ANGER
    assert again.selection.filters.date_to is not None
    assert again.selection.filters.date_to.isoformat() == "2026-03-01"


# -- context notes ------------------------------------------------------------


def note(**changes: object) -> NoteDraft:
    base = {
        "association": ContextAssociation.TOPIC,
        "association_value": "shipping",
        "phrase": "running late",
        "explanation": "A common phrase in this group.",
        "context_importance": "It may signal delay rather than anger.",
        "tags": (ContextTag.IDIOM_OR_SLANG,),
    }
    return NoteDraft(**{**base, **changes})  # type: ignore[arg-type]


def test_a_note_is_stored_apart_from_the_ai_and_human_state(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    accept_both(tmp_path, project_id, 1)
    before = repository(tmp_path).get(project_id)
    assert before is not None

    insights(tmp_path).add_note(project_id, note())

    after = repository(tmp_path).get(project_id)
    assert after is not None
    assert after.result == before.result  # the AI results are untouched
    assert after.reviews == before.reviews  # so are the human reviews
    (stored,) = insights(tmp_path).open_insights(project_id).notes
    assert (stored.association_value, stored.phrase) == ("shipping", "running late")
    assert stored.tags == (ContextTag.IDIOM_OR_SLANG,)


@pytest.mark.parametrize(
    ("changes", "field", "code"),
    [
        ({"phrase": "   "}, "phrase", "required"),
        ({"explanation": "x" * 2001}, "explanation", "too_long"),
        ({"phrase": "x" * 501}, "phrase", "too_long"),
        (
            {"association_value": "unknown topic"},
            "association_value",
            "unknown_association",
        ),
        (
            {"tags": tuple(ContextTag)[:8] + (ContextTag.OTHER,) * 1},
            "tags",
            "invalid_tags",
        ),
    ],
)
def test_an_invalid_note_is_refused_and_nothing_is_stored(
    tmp_path: Path, changes: dict[str, object], field: str, code: str
) -> None:
    project_id = analysed(tmp_path)

    with pytest.raises(ValidationError) as failure:
        insights(tmp_path).add_note(project_id, note(**changes))

    assert (failure.value.field, failure.value.code) == (field, code)
    assert insights(tmp_path).open_insights(project_id).notes == ()


def test_removing_a_note_removes_only_that_note(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.add_note(project_id, note(phrase="first"))
    flow.add_note(project_id, note(phrase="second"))
    first, second = flow.open_insights(project_id).notes

    flow.remove_note(project_id, first.note_id)

    assert [n.phrase for n in insights(tmp_path).open_insights(project_id).notes] == [
        "second"
    ]
    with pytest.raises(ValidationError) as failure:
        flow.remove_note(project_id, first.note_id)
    assert failure.value.code == "note_not_found"
    assert second.note_id in {
        n.note_id for n in insights(tmp_path).open_insights(project_id).notes
    }


class RacingRepository(SqliteProjectRepository):
    """Runs a hook at the moment this process commits a mutation."""

    def __init__(self, root: Path) -> None:
        super().__init__(AppDataLocations(root))
        self.before_mutate: Callable[[], object] | None = None

    def mutate(
        self,
        token: str,
        mutation: Callable[[BatchWorkspace], BatchWorkspace],
    ) -> BatchWorkspace | None:
        hook, self.before_mutate = self.before_mutate, None
        if hook is not None:
            hook()
        return super().mutate(token, mutation)


def test_a_note_added_while_another_process_saves_keeps_both_changes(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    mine = RacingRepository(tmp_path)

    def elsewhere() -> None:
        accept_both(tmp_path, project_id, 2)  # a newer human review
        insights(tmp_path).add_note(project_id, note(phrase="theirs"))  # a newer note

    mine.before_mutate = elsewhere

    InsightsWorkflow(mine).add_note(project_id, note(phrase="mine"))

    final = insights(tmp_path).open_insights(project_id)
    assert sorted(n.phrase for n in final.notes) == ["mine", "theirs"]
    kept = ReviewWorkflow(repository(tmp_path)).open_review(project_id, row=2)
    assert kept.record is not None and kept.record.review.is_reviewed


def test_removing_a_note_keeps_another_process_newer_state(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.add_note(project_id, note(phrase="old"))
    (old,) = flow.open_insights(project_id).notes
    mine = RacingRepository(tmp_path)

    def elsewhere() -> None:
        accept_both(tmp_path, project_id, 3)
        insights(tmp_path).add_note(project_id, note(phrase="newer"))

    mine.before_mutate = elsewhere

    InsightsWorkflow(mine).remove_note(project_id, old.note_id)

    final = insights(tmp_path).open_insights(project_id)
    assert [n.phrase for n in final.notes] == ["newer"]
    kept = ReviewWorkflow(repository(tmp_path)).open_review(project_id, row=3)
    assert kept.record is not None and kept.record.review.is_reviewed


def test_applying_a_view_keeps_notes_and_reviews_added_elsewhere(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    mine = RacingRepository(tmp_path)

    def elsewhere() -> None:
        accept_both(tmp_path, project_id, 4)
        insights(tmp_path).add_note(project_id, note(phrase="theirs"))

    mine.before_mutate = elsewhere

    InsightsWorkflow(mine).apply(project_id, controls(groups=("shipping",)))

    final = insights(tmp_path).open_insights(project_id)
    assert [n.phrase for n in final.notes] == ["theirs"]
    assert final.selection.groups == ("shipping",)
    kept = ReviewWorkflow(repository(tmp_path)).open_review(project_id, row=4)
    assert kept.record is not None and kept.record.review.is_reviewed


def correct_to_positive(root: Path, project_id: str, row: int) -> None:
    review(
        root,
        project_id,
        row,
        ReviewDraft(
            sentiment_judgment=CORRECT,
            human_sentiment=SentimentLabel.POSITIVE,
            emotion_judgment=CORRECT,
            human_dominant_emotion=EmotionLabel.JOY,
        ),
    )


@pytest.mark.parametrize(
    ("perspective", "metric", "expected"),
    [
        (
            InsightPerspective.AGREEMENT,
            InsightMetric.SENTIMENT_DISAGREEMENT,
            {"disagreement": (1, 1), "agreement": (0, 1)},
        ),
        (
            InsightPerspective.HUMAN,
            InsightMetric.HUMAN_SENTIMENT,
            {"positive": (1, 1)},
        ),
    ],
)
def test_a_view_applied_while_a_review_is_saved_elsewhere_is_one_current_state(
    tmp_path: Path,
    perspective: InsightPerspective,
    metric: InsightMetric,
    expected: dict[str, tuple[int, int]],
) -> None:
    project_id = analysed(tmp_path)  # nothing is reviewed yet
    mine = RacingRepository(tmp_path)

    def elsewhere() -> None:
        correct_to_positive(tmp_path, project_id, 5)  # changes the metric population
        insights(tmp_path).add_note(project_id, note(phrase="theirs"))

    mine.before_mutate = elsewhere

    snapshot = InsightsWorkflow(mine).apply(
        project_id,
        controls(perspective=perspective, metric=metric),
        ExampleControls(mode=ExampleMode.HUMAN_CORRECTED),
    )

    (shipping,) = snapshot.summaries
    assert expected.items() <= counts(shipping).items()  # includes the newer review
    assert shipping.eligible_count == 1
    assert shipping.unreviewed_count == 11
    assert rows_of(snapshot) == [5]  # the examples come from the same state
    assert [n.phrase for n in snapshot.notes] == ["theirs"]
    assert snapshot.summaries == insights(tmp_path).open_insights(project_id).summaries


# -- representative cases -----------------------------------------------------


def rows_of(snapshot: object) -> list[int]:
    return [e.outcome.prepared.row_number for e in snapshot.examples]  # type: ignore[attr-defined]


def test_highest_ai_score_names_its_emotion_and_orders_by_score(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).open_insights(
        project_id,
        examples=ExampleControls(
            mode=ExampleMode.HIGHEST_AI_SCORE, emotion=EmotionLabel.ANGER
        ),
    )

    assert rows_of(snapshot) == [5, 6, 7, 8, 13]  # the angry rows, by row on a tie
    assert {e.reason for e in snapshot.examples} == {"Highest AI compact anger score"}


def test_lowest_ai_confidence_is_the_default_rule(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)

    snapshot = insights(tmp_path).open_insights(project_id)

    assert snapshot.example_mode is ExampleMode.LOWEST_AI_CONFIDENCE
    assert len(snapshot.examples) == 5
    assert {e.reason for e in snapshot.examples} == {"Lowest displayed AI confidence"}


def test_review_based_rules_show_their_reasons_and_the_human_judgment(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    review(
        tmp_path,
        project_id,
        5,
        ReviewDraft(
            sentiment_judgment=CORRECT,
            human_sentiment=SentimentLabel.POSITIVE,
            emotion_judgment=ACCEPT,
        ),
    )
    review(
        tmp_path,
        project_id,
        6,
        ReviewDraft(sentiment_judgment=UNCERTAIN, emotion_judgment=UNCERTAIN),
    )
    flow = insights(tmp_path)

    disagreement = flow.open_insights(
        project_id, examples=ExampleControls(mode=ExampleMode.AI_HUMAN_DISAGREEMENT)
    )
    corrected = flow.open_insights(
        project_id, examples=ExampleControls(mode=ExampleMode.HUMAN_CORRECTED)
    )
    uncertain = flow.open_insights(
        project_id, examples=ExampleControls(mode=ExampleMode.UNCERTAIN)
    )

    assert rows_of(disagreement) == [5]
    assert disagreement.examples[0].reason.startswith("Highest definitive AI-human")
    assert disagreement.examples[0].review is not None
    assert disagreement.examples[0].review.human_sentiment is SentimentLabel.POSITIVE
    assert rows_of(corrected) == [5]
    assert corrected.examples[0].reason == "Human-corrected review"
    assert rows_of(uncertain) == [6]
    assert uncertain.examples[0].reason == "Human review marked uncertain"


def test_context_note_and_user_selected_rules(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.add_note(
        project_id,
        note(
            association=ContextAssociation.RECORD,
            association_value="r7",
            tags=(ContextTag.SARCASM_POSSIBLE,),
        ),
    )
    flow.add_note(
        project_id,
        note(association=ContextAssociation.RECORD, association_value="r9", tags=()),
    )

    any_note = flow.open_insights(
        project_id, examples=ExampleControls(mode=ExampleMode.CONTEXT_NOTES)
    )
    tagged = flow.open_insights(
        project_id,
        examples=ExampleControls(
            mode=ExampleMode.CONTEXT_NOTES, tag=ContextTag.SARCASM_POSSIBLE
        ),
    )
    chosen = flow.open_insights(
        project_id,
        examples=ExampleControls(
            mode=ExampleMode.USER_SELECTED, record_ids=("r2", "r11")
        ),
    )

    assert rows_of(any_note) == [7, 9]
    assert any_note.examples[0].reason == "Record has a user-authored context note"
    assert rows_of(tagged) == [7]
    assert tagged.examples[0].reason.endswith("tagged sarcasm_possible")
    assert rows_of(chosen) == [2, 11]
    assert chosen.examples[0].reason == "Explicitly selected by the user"
    assert chosen.selected_record_ids == frozenset({"r2", "r11"})


def test_changing_the_example_rule_does_not_change_the_saved_view(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.apply(project_id, controls(groups=("billing", "shipping"), comparison=True))

    flow.open_insights(
        project_id,
        examples=ExampleControls(mode=ExampleMode.UNCERTAIN),
        comparison=True,
    )

    assert flow.open_insights(project_id).selection.groups == ("billing", "shipping")


# -- export -------------------------------------------------------------------


def test_the_export_follows_the_existing_contract_and_options(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.apply(project_id, controls(groups=("shipping",)))
    flow.add_note(project_id, note(phrase="=HYPERLINK(1)"))

    plain = flow.export_csv(project_id)
    with_records = flow.export_csv(project_id, include_records=True)
    native = flow.export_csv(project_id, include_records=True, include_native=True)

    plain_rows = list(csv.DictReader(io.StringIO(plain)))
    sections = {r["section"] for r in plain_rows}
    assert sections == {"export_metadata", "group_summary", "context_note"}
    note_row = next(r for r in plain_rows if r["section"] == "context_note")
    assert note_row["phrase"] == "'=HYPERLINK(1)"  # spreadsheet-safe
    assert "supporting_record" not in sections
    records = [
        r
        for r in csv.DictReader(io.StringIO(with_records))
        if r["section"] == "supporting_record"
    ]
    assert len(records) == 12 and all(SENTINEL in r["text"] for r in records)
    assert all(r["native_emotion_scores"] == "" for r in records)
    native_records = [
        r
        for r in csv.DictReader(io.StringIO(native))
        if r["section"] == "supporting_record"
    ]
    assert all(r["native_emotion_scores"] for r in native_records)


def test_a_comparison_export_needs_two_to_four_groups(tmp_path: Path) -> None:
    project_id = analysed(tmp_path)
    flow = insights(tmp_path)
    flow.apply(project_id, controls(groups=("shipping",)))

    with pytest.raises(ValidationError) as failure:
        flow.export_csv(project_id, comparison=True)

    assert failure.value.code == "comparison_group_count"


# -- availability and isolation -----------------------------------------------


def test_only_an_analysed_project_has_insights(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), VariedGateway(), LIMITS)
    ready = flow.import_csv(insights_csv(), name="P").summary.project_id

    with pytest.raises(InsightsUnavailableError):
        insights(tmp_path).open_insights(ready)
    with pytest.raises(ProjectNotFoundError):
        insights(tmp_path).open_insights("0" * 32)


def test_a_project_with_no_successful_rows_has_no_insights(tmp_path: Path) -> None:
    flow = ProjectWorkflow(repository(tmp_path), VariedGateway(), LIMITS)
    project_id = flow.import_csv(
        f"record_id,text\nr1,{SENTINEL} {'FAILME'}\n".encode(), name="P"
    ).summary.project_id
    flow.analyze(project_id)

    with pytest.raises(InsightsUnavailableError):
        insights(tmp_path).open_insights(project_id)


def test_viewing_and_exporting_never_change_results_or_reviews(
    tmp_path: Path,
) -> None:
    project_id = analysed(tmp_path)
    accept_both(tmp_path, project_id, 1)
    before = repository(tmp_path).get(project_id)
    assert before is not None
    flow = insights(tmp_path)

    flow.apply(project_id, controls(groups=("billing", "shipping"), comparison=True))
    flow.open_insights(
        project_id, examples=ExampleControls(mode=ExampleMode.HUMAN_CORRECTED)
    )
    flow.export_csv(project_id, include_records=True, include_native=True)

    after = repository(tmp_path).get(project_id)
    assert after is not None
    assert (after.preview, after.result, after.reviews) == (
        before.preview,
        before.result,
        before.reviews,
    )
