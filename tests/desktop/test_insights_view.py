"""Pure insights view models: honest wording, denominators, and separation (no Qt)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from persistence.insight_samples import VariedGateway, insights_csv

from social_text_intelligence.application.insights_workflow import (
    ContextAssociation,
    ContextTag,
    ExampleControls,
    ExampleMode,
    GroupingDimension,
    InsightControls,
    InsightMetric,
    InsightPerspective,
    InsightsSnapshot,
    InsightsWorkflow,
    NoteDraft,
)
from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.review_workflow import (
    ReviewDraft,
    ReviewJudgment,
    ReviewWorkflow,
)
from social_text_intelligence.contracts import SentimentLabel
from social_text_intelligence.desktop.insights import (
    InsightsActivity,
    InsightsState,
)
from social_text_intelligence.desktop.insights_view import (
    LIMITATIONS,
    build_insights_view,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)

LIMITS = CsvLimits(max_bytes=50_000, max_rows=100, max_text_length=500)


class Fixture:
    def __init__(self, root: Path) -> None:
        self.repository = SqliteProjectRepository(AppDataLocations(root))
        flow = ProjectWorkflow(self.repository, VariedGateway(), LIMITS)
        self.project_id = flow.import_csv(insights_csv(), name="P").summary.project_id
        flow.analyze(self.project_id)
        self.insights = InsightsWorkflow(self.repository)
        self.reviews = ReviewWorkflow(self.repository)

    def state(self, snapshot: InsightsSnapshot, **changes: object) -> InsightsState:
        base = InsightsState(
            project_id=self.project_id,
            snapshot=snapshot,
            controls=InsightControls.from_selection(
                snapshot.selection, comparison=snapshot.comparison
            ),
        )
        return replace(base, **changes)  # type: ignore[arg-type]

    def apply(self, **changes: object) -> InsightsSnapshot:
        base: dict[str, object] = {
            "grouping": GroupingDimension.TOPIC,
            "groups": ("shipping",),
            "perspective": InsightPerspective.AI,
            "metric": InsightMetric.AI_SENTIMENT,
        }
        return self.insights.apply(
            self.project_id,
            InsightControls(**{**base, **changes}),  # type: ignore[arg-type]
        )


@pytest.fixture
def fx(tmp_path: Path) -> Fixture:
    return Fixture(tmp_path)


def test_a_group_card_shows_counts_with_denominators_and_the_definition(
    fx: Fixture,
) -> None:
    view = build_insights_view(fx.state(fx.apply()))

    assert view is not None
    (card,) = view.cards
    assert card.heading == "shipping"
    rows = {row.label: (row.count_text, row.percent_text) for row in card.rows}
    assert rows["Positive"] == ("4 / 12", "33.3%")
    assert rows["Negative"] == ("4 / 12", "33.3%")
    assert "12 eligible for this metric" in card.context_line
    assert "group has 13 rows" in card.context_line
    assert "1 failed row assigned to this group" in card.failed_line
    assert card.sample_line is None  # 12 eligible rows: no warning
    assert "denominator is successful rows" in view.definition_line


def test_small_and_insufficient_samples_keep_the_service_warnings(fx: Fixture) -> None:
    view = build_insights_view(
        fx.state(fx.apply(groups=("billing", "returns", "shipping"), comparison=True))
    )

    assert view is not None
    billing, returns, shipping = view.cards
    assert billing.sample_line == "Small sample"
    assert returns.sample_line is not None
    assert returns.sample_line.startswith("Insufficient sample for comparison")
    assert "comparative emphasis is suppressed" in returns.sample_line
    assert {row.percent_text for row in returns.rows} == {"Percentage de-emphasized"}
    assert shipping.sample_line is None
    assert view.comparison_caution is not None
    assert "returns" in view.comparison_caution and "billing" in view.comparison_caution
    assert "shipping" not in view.comparison_caution


def test_a_clean_comparison_has_no_caution(fx: Fixture) -> None:
    ok = fx.apply(groups=("shipping",))  # a single, large group
    assert build_insights_view(fx.state(ok)).comparison_caution is None  # type: ignore[union-attr]


def test_review_populations_are_described_for_human_and_agreement_views(
    fx: Fixture,
) -> None:
    seen = fx.reviews.open_review(fx.project_id, row=1).record
    assert seen is not None
    fx.reviews.accept_both(fx.project_id, 1, "", expected=seen.review)

    human = build_insights_view(
        fx.state(
            fx.apply(
                perspective=InsightPerspective.HUMAN,
                metric=InsightMetric.HUMAN_SENTIMENT,
            )
        )
    )
    agreement = build_insights_view(
        fx.state(
            fx.apply(
                perspective=InsightPerspective.AGREEMENT,
                metric=InsightMetric.SENTIMENT_DISAGREEMENT,
            )
        )
    )

    assert human is not None and agreement is not None
    assert "11 unreviewed" in human.cards[0].review_line
    assert "definitive" in human.definition_line
    assert "not model accuracy" in agreement.definition_line
    text = " ".join(
        [
            agreement.definition_line,
            LIMITATIONS,
            *(c.accessible_name for c in agreement.cards),
        ]
    ).lower()
    for forbidden in ("calibrat", "model quality", "operator", "detected"):
        assert forbidden not in text
    assert "agreement is not accuracy" in LIMITATIONS.lower()


def test_an_ai_view_does_not_show_review_counts(fx: Fixture) -> None:
    view = build_insights_view(fx.state(fx.apply()))

    assert view is not None and view.cards[0].review_line == ""


def test_the_language_grouping_says_it_comes_from_the_file(fx: Fixture) -> None:
    view = build_insights_view(
        fx.state(fx.apply(grouping=GroupingDimension.LANGUAGE, groups=("en",)))
    )

    assert view is not None
    labels = {value: label for label, value in view.grouping_choices}
    assert "supplied" in labels["language"].lower()
    assert "detect" not in " ".join(labels.values()).lower()


def test_metric_choices_follow_the_perspective(fx: Fixture) -> None:
    ai = build_insights_view(fx.state(fx.apply()))
    human_controls = InsightControls(
        grouping=GroupingDimension.TOPIC,
        groups=("shipping",),
        perspective=InsightPerspective.HUMAN,
        metric=InsightMetric.HUMAN_SENTIMENT,
    )
    human = build_insights_view(fx.state(fx.apply(), controls=human_controls))

    assert ai is not None and human is not None
    assert [v for _, v in ai.metric_choices] == [
        "ai_sentiment",
        "ai_dominant_emotion",
        "ai_emotion_activation",
    ]
    assert [v for _, v in human.metric_choices] == [
        "human_sentiment",
        "human_dominant_emotion",
        "human_emotion_inclusion",
    ]
    assert [g for g, _ in ai.group_choices][:2] == ["billing", "returns"]
    assert dict(ai.group_choices)["shipping"] is True  # the displayed group is ticked


def test_a_note_is_human_context_apart_from_every_ai_and_review_value(
    fx: Fixture,
) -> None:
    fx.insights.add_note(
        fx.project_id,
        NoteDraft(
            association=ContextAssociation.RECORD,
            association_value="r7",
            phrase="running late",
            explanation="Common phrase.",
            context_importance="Means delay.",
            tags=(ContextTag.IDIOM_OR_SLANG,),
        ),
    )

    view = build_insights_view(fx.state(fx.apply()))

    assert view is not None
    (note,) = view.notes
    assert "your context note" in note.heading.lower()
    assert "not ai output" in note.heading.lower()
    assert note.phrase == "running late"
    assert "record: r7" in note.subtitle.lower()
    assert "idiom or slang" in note.tags_line.lower()
    assert "Delete note" in note.delete_label
    assert view.note_value_choices[ContextAssociation.TOPIC][0] == "billing"
    assert view.note_value_choices[ContextAssociation.RECORD][0] == "r1"


def test_a_case_shows_why_it_was_chosen_with_ai_and_human_apart(fx: Fixture) -> None:
    seen = fx.reviews.open_review(fx.project_id, row=5).record
    assert seen is not None
    fx.reviews.save(
        fx.project_id,
        5,
        ReviewDraft(
            sentiment_judgment=ReviewJudgment.CORRECT,
            human_sentiment=SentimentLabel.POSITIVE,
            emotion_judgment=ReviewJudgment.ACCEPT,
        ),
        expected=seen.review,
    )
    snapshot = fx.insights.open_insights(
        fx.project_id,
        examples=ExampleControls(mode=ExampleMode.AI_HUMAN_DISAGREEMENT),
    )

    view = build_insights_view(fx.state(snapshot))

    assert view is not None
    (case,) = view.cases
    assert case.reason.startswith("Why shown: Highest definitive AI-human")
    assert case.title == "Row 5 · r5"
    assert "Negative" in case.ai_line and "80.0%" in case.ai_line
    assert "AI record" in case.ai_heading and "Human judgment" in case.human_heading
    assert case.ai_heading != case.human_heading
    assert "Positive" in case.human_line
    assert "Partly reviewed" in case.human_line or "Reviewed" in case.human_line


def test_a_case_without_a_review_entry_says_so(fx: Fixture) -> None:
    snapshot = fx.insights.open_insights(fx.project_id)

    view = build_insights_view(fx.state(snapshot))

    assert view is not None
    assert "Unreviewed" in view.cases[0].human_line
    assert len(view.cases) == 5


def test_the_example_choices_name_every_rule_and_the_selected_records(
    fx: Fixture,
) -> None:
    snapshot = fx.insights.open_insights(
        fx.project_id,
        examples=ExampleControls(mode=ExampleMode.USER_SELECTED, record_ids=("r2",)),
    )

    view = build_insights_view(
        fx.state(
            snapshot,
            examples=ExampleControls(
                mode=ExampleMode.USER_SELECTED, record_ids=("r2",)
            ),
        )
    )

    assert view is not None
    assert [v for _, v in view.example_mode_choices] == [m.value for m in ExampleMode]
    assert "neutral" not in [v for _, v in view.example_emotion_choices]
    assert dict(view.record_choices)["r2"] is True
    assert dict(view.record_choices)["r1"] is False
    assert view.cases[0].reason == "Why shown: Explicitly selected by the user"


def test_buttons_follow_the_busy_state_and_unsaved_note(fx: Fixture) -> None:
    snapshot = fx.apply()

    idle = build_insights_view(fx.state(snapshot))
    busy = build_insights_view(fx.state(snapshot, activity=InsightsActivity.APPLYING))
    writing = build_insights_view(fx.state(snapshot, note_draft=NoteDraft(phrase="x")))

    assert idle is not None and busy is not None and writing is not None
    assert idle.controls_enabled and idle.apply_enabled and idle.export_enabled
    assert not idle.unsaved and not idle.add_note_enabled  # nothing written yet
    assert not (busy.controls_enabled or busy.apply_enabled or busy.export_enabled)
    assert writing.unsaved and writing.add_note_enabled


def test_a_comparison_needs_two_groups_before_apply_is_offered(fx: Fixture) -> None:
    snapshot = fx.apply()
    one = replace(
        InsightControls.from_selection(snapshot.selection, comparison=True),
        groups=("shipping",),
    )
    two = replace(one, groups=("shipping", "billing"))

    one_view = build_insights_view(fx.state(snapshot, controls=one))
    two_view = build_insights_view(fx.state(snapshot, controls=two))

    assert one_view is not None and two_view is not None
    assert not one_view.apply_enabled
    assert "two to four" in one_view.group_hint.lower()
    assert two_view.apply_enabled


def test_the_export_note_says_which_view_is_exported(fx: Fixture) -> None:
    from social_text_intelligence.desktop.insights_view import EXPORT_NOTE

    assert "last shown" in EXPORT_NOTE


def test_a_confidence_figure_is_not_presented_as_a_probability(fx: Fixture) -> None:
    from social_text_intelligence.desktop.insights_view import CASES_NOTE

    view = build_insights_view(fx.state(fx.insights.open_insights(fx.project_id)))

    assert view is not None and "confidence 80.0%" in view.cases[0].ai_line
    assert "not calibrated" in CASES_NOTE
