"""The language check where a person would otherwise read model labels unwarned."""

from __future__ import annotations

from typing import Any

from social_text_intelligence.desktop.analysis import result_view

from .fakes import FakeProvisioning, StubGateway, status, synthetic_report


def test_an_unsupported_language_is_flagged_beside_an_unchanged_result() -> None:
    plain = result_view(synthetic_report())
    flagged = result_view(synthetic_report(detected="fr"))

    assert flagged.language_warns
    assert "French (fr)" in flagged.language_headline
    assert "still analysed" in flagged.language_detail
    assert (flagged.sentiment, flagged.emotion, flagged.secondary_emotions) == (
        plain.sentiment,
        plain.emotion,
        plain.secondary_emotions,
    )  # the labels are exactly what the models said


def test_a_supported_language_is_stated_without_a_warning() -> None:
    view = result_view(synthetic_report(detected="en"))

    assert not view.language_warns
    assert "English (en)" in view.language_headline


def test_typed_text_that_cannot_be_judged_is_not_confidently_determined() -> None:
    view = result_view(synthetic_report("ok", detected=None))

    assert view.language_warns
    assert "not confidently determined" in view.language_headline


def test_a_result_with_no_language_check_says_not_assessed_without_a_warning() -> None:
    view = result_view(synthetic_report())

    assert not view.language_warns
    assert "not assessed" in view.language_headline.lower()


# -- the real Qt page ----------------------------------------------------------

def analyse(make_shell: Any, report: Any) -> Any:
    shell = make_shell(
        FakeProvisioning(current=status()), gateway=StubGateway(report=report)
    )
    shell.window.show_page("Analyze one text")
    page = shell.window.analyze_page
    page.editor.setPlainText("Some text to analyse.")
    page.analyze_button.click()
    return page


def test_the_analyze_page_warns_in_words_and_keeps_the_labels(make_shell: Any) -> None:
    page = analyse(make_shell, synthetic_report(detected="fr"))

    assert page.result_box.isVisibleTo(page)
    assert "Sentiment:" in page.result_text.text()
    assert page.language_box.isVisibleTo(page)
    assert page.language_box.property("role") == "notice"
    assert page.language_headline.text().startswith("⚠ ")
    assert "French (fr)" in page.language_headline.text()
    assert "still analysed" in page.language_detail.text()


def test_the_analyze_page_does_not_warn_for_a_supported_language(
    make_shell: Any,
) -> None:
    page = analyse(make_shell, synthetic_report(detected="en"))

    assert page.language_box.property("role") == "panel"
    assert not page.language_headline.text().startswith("⚠")
    assert "English (en)" in page.language_headline.text()


def test_the_analyze_page_says_not_assessed_when_no_check_ran(make_shell: Any) -> None:
    page = analyse(make_shell, synthetic_report())

    assert "not assessed" in page.language_headline.text().lower()
    assert page.language_box.property("role") == "panel"


# -- project summary -------------------------------------------------------------


def project_view(language: Any, phase: Any = None) -> Any:
    from datetime import UTC, datetime

    from social_text_intelligence.application.project_workflow import (
        ProjectDetails,
        ProjectPhase,
    )
    from social_text_intelligence.application.projects import (
        ProjectStatus,
        ProjectSummary,
    )
    from social_text_intelligence.desktop.gate import AnalysisAvailability
    from social_text_intelligence.desktop.projects import ProjectsState
    from social_text_intelligence.desktop.projects_view import build_detail_view

    summary = ProjectSummary(
        "ab" * 16, ProjectStatus.OK, "Tickets", datetime(2026, 1, 2, tzinfo=UTC), None
    )
    details = ProjectDetails(
        summary,
        phase or ProjectPhase.ANALYZED,
        headers=("text",),
        text_column="text",
        row_count=8,
        valid_rows=8,
        analyzed_rows=8,
        failed_rows=0,
        language=language,
    )
    return build_detail_view(
        ProjectsState(current=details), AnalysisAvailability.AVAILABLE, status()
    )


def test_an_analysed_project_summarises_the_language_check() -> None:
    from social_text_intelligence.application.language import summarize_languages

    from .fakes import synthetic_report

    reports = [synthetic_report(detected=code) for code in ("en", "fr", "fr", None)]
    summary = summarize_languages(r.language for r in reports)
    view = project_view(summary)

    assert view.language_warns
    assert "3 of 4" in view.language_headline
    assert "French (fr) 2" in view.language_detail


def test_a_project_with_nothing_analysed_has_no_language_line() -> None:
    from social_text_intelligence.application.project_workflow import ProjectPhase

    view = project_view(None, ProjectPhase.READY)

    assert view.language_headline is None and not view.language_warns


def test_the_project_page_shows_the_language_summary_after_analysis(
    make_shell: Any, tmp_path: Any
) -> None:
    from persistence.language_samples import LanguageGateway, mixed_language_csv

    shell = make_shell(
        FakeProvisioning(current=status()), gateway=LanguageGateway()
    )
    page = shell.window.projects_page
    path = tmp_path / "mixed.csv"
    path.write_bytes(mixed_language_csv())
    shell.platform.csv_file = path
    shell.button(page, "Import CSV…").click()
    assert not page.language_box.isVisibleTo(page)  # nothing analysed yet

    page.analyze_button.click()

    assert page.language_box.isVisibleTo(page)
    assert page.language_box.property("role") == "notice"
    assert "3 of 5" in page.language_box.headline.text()
    assert "French (fr) 2" in page.language_box.detail.text()
    assert "Language check" in page.language_box.accessibleName()


# -- the review record --------------------------------------------------------------


def review_view_of(tmp_path: Any, row: int) -> Any:
    from persistence.language_samples import LanguageGateway, mixed_language_csv

    from social_text_intelligence.application.project_workflow import (
        CsvLimits,
        ProjectWorkflow,
    )
    from social_text_intelligence.application.review_workflow import ReviewWorkflow
    from social_text_intelligence.desktop.review import ReviewState
    from social_text_intelligence.desktop.review_view import build_review_view
    from social_text_intelligence.infrastructure.app_data import AppDataLocations
    from social_text_intelligence.infrastructure.sqlite_projects import (
        SqliteProjectRepository,
    )

    repository = SqliteProjectRepository(AppDataLocations(tmp_path))
    limits = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
    flow = ProjectWorkflow(repository, LanguageGateway(), limits)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id
    flow.analyze(project_id)
    snapshot = ReviewWorkflow(repository).open_review(project_id, row=row)
    return build_review_view(ReviewState(project_id=project_id, snapshot=snapshot))


def test_a_review_record_shows_supplied_and_detected_language_apart(
    tmp_path: Any,
) -> None:
    view = review_view_of(tmp_path, 2)  # supplied en, but the text is French

    record = view.record
    assert "Language supplied in the file: en" in record.context
    assert not any("French" in line for line in record.context)
    assert record.language_warns
    assert "French (fr)" in record.language_headline
    assert "Language:" not in "".join(record.context)  # no ambiguous "Language: en"
    assert "French" not in record.ai.sentiment_line + record.ai.emotion_line


def test_a_missing_supplied_language_is_not_english(tmp_path: Any) -> None:
    view = review_view_of(tmp_path, 4)

    assert "Language supplied in the file: not supplied" in view.record.context


def test_a_supported_record_shows_the_detected_language_without_a_warning(
    tmp_path: Any,
) -> None:
    view = review_view_of(tmp_path, 3)  # supplied fr, detected English

    assert "Language supplied in the file: fr" in view.record.context
    assert not view.record.language_warns
    assert "English (en)" in view.record.language_headline


def _review_page(make_shell: Any, tmp_path: Any, row: int) -> Any:
    from persistence.language_samples import LanguageGateway, mixed_language_csv

    shell = make_shell(FakeProvisioning(current=status()), gateway=LanguageGateway())
    page = shell.window.projects_page
    path = tmp_path / "mixed.csv"
    path.write_bytes(mixed_language_csv())
    shell.platform.csv_file = path
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    page.review_button.click()
    review = page.review_page
    while "Row " + str(row) not in review.record_title.text():
        review.next_button.click()
    return review


def test_the_review_page_warns_beside_the_ai_block_and_keeps_it_labels_only(
    make_shell: Any, tmp_path: Any
) -> None:
    review = _review_page(make_shell, tmp_path, 2)

    box = review.language_box
    assert box.isVisibleTo(review) and box.property("role") == "notice"
    assert "French (fr)" in box.headline.text()
    assert "Language supplied in the file: en" in review.record_context.text()
    ai_text = " ".join(
        w.text() for w in review.ai.findChildren(type(review.record_context))
    )
    assert "French" not in ai_text and "language" not in ai_text.lower()


def test_the_review_page_is_quiet_when_the_language_is_supported(
    make_shell: Any, tmp_path: Any
) -> None:
    review = _review_page(make_shell, tmp_path, 1)

    assert review.language_box.property("role") == "panel"
    assert "English (en)" in review.language_box.headline.text()


# -- insights ----------------------------------------------------------------------


def insights_view_of(tmp_path: Any, group: str = "en") -> Any:
    from dataclasses import replace

    from persistence.language_samples import LanguageGateway, mixed_language_csv

    from social_text_intelligence.application.insights_workflow import (
        ExampleControls,
        ExampleMode,
        GroupingDimension,
        InsightControls,
        InsightMetric,
        InsightPerspective,
        InsightsWorkflow,
    )
    from social_text_intelligence.application.project_workflow import (
        CsvLimits,
        ProjectWorkflow,
    )
    from social_text_intelligence.desktop.insights import InsightsState
    from social_text_intelligence.desktop.insights_view import build_insights_view
    from social_text_intelligence.infrastructure.app_data import AppDataLocations
    from social_text_intelligence.infrastructure.sqlite_projects import (
        SqliteProjectRepository,
    )

    repository = SqliteProjectRepository(AppDataLocations(tmp_path))
    limits = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)
    flow = ProjectWorkflow(repository, LanguageGateway(), limits)
    project_id = flow.import_csv(mixed_language_csv(), name="P").summary.project_id
    flow.analyze(project_id)
    examples = ExampleControls(mode=ExampleMode.LOWEST_AI_CONFIDENCE)
    snapshot = InsightsWorkflow(repository).apply(
        project_id,
        InsightControls(
            grouping=GroupingDimension.LANGUAGE,
            groups=(group,),
            perspective=InsightPerspective.AI,
            metric=InsightMetric.AI_SENTIMENT,
        ),
        examples,
    )
    state = replace(
        InsightsState(
            project_id=project_id,
            snapshot=snapshot,
            controls=InsightControls.from_selection(
                snapshot.selection, comparison=False
            ),
        ),
        examples=examples,
    )
    return build_insights_view(state)


def test_the_insights_page_says_how_many_texts_are_outside_the_models_language(
    tmp_path: Any,
) -> None:
    view = insights_view_of(tmp_path)

    assert view.language_warns
    assert "3 of 5" in view.language_headline
    (card,) = view.cards
    assert "2 of 3" in card.language_line
    assert "still counted" in card.language_line  # metrics are unchanged


def test_a_case_keeps_the_language_notice_apart_from_ai_and_human(
    tmp_path: Any,
) -> None:
    view = insights_view_of(tmp_path)

    case = next(c for c in view.cases if c.title.endswith("r2"))
    assert case.language_warns and "French (fr)" in case.language_headline
    assert "French" not in case.ai_line + case.human_line


def test_a_supported_group_has_no_language_caveat_line(tmp_path: Any) -> None:
    view = insights_view_of(tmp_path, "fr")  # the single English text, supplied fr

    (card,) = view.cards
    assert card.language_line == ""


def _insights_page(make_shell: Any, tmp_path: Any) -> Any:
    from persistence.language_samples import LanguageGateway, mixed_language_csv
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QComboBox

    shell = make_shell(FakeProvisioning(current=status()), gateway=LanguageGateway())
    page = shell.window.projects_page
    path = tmp_path / "mixed.csv"
    path.write_bytes(mixed_language_csv())
    shell.platform.csv_file = path
    shell.button(page, "Import CSV…").click()
    page.analyze_button.click()
    page.insights_button.click()
    insights = page.insights_page
    grouping: QComboBox = insights.grouping_combo
    grouping.setCurrentIndex(grouping.findData("language"))
    grouping.activated.emit(grouping.currentIndex())
    for i in range(insights.group_list.count()):
        item = insights.group_list.item(i)
        item.setCheckState(
            Qt.CheckState.Checked if item.text() == "en" else Qt.CheckState.Unchecked
        )
    insights.apply_button.click()
    return insights


def test_the_insights_page_shows_the_project_language_caveat_and_group_line(
    make_shell: Any, tmp_path: Any
) -> None:
    insights = _insights_page(make_shell, tmp_path)

    box = insights.language_box
    assert box.isVisibleTo(insights) and box.property("role") == "notice"
    assert "3 of 5" in box.headline.text()
    group_note = insights.findChild(type(insights.caution), "group-language")
    assert group_note is not None and "2 of 3" in group_note.text()
    assert "Language (as supplied in the file)" in insights.grouping_combo.currentText()


def test_the_cases_view_warns_per_case_beside_ai_and_human(
    make_shell: Any, tmp_path: Any
) -> None:
    insights = _insights_page(make_shell, tmp_path)
    insights.tabs.setCurrentIndex(1)
    insights.select_button.click()

    boxes = insights.findChildren(type(insights.language_box), "case-language")

    assert boxes
    assert any("French (fr)" in box.headline.text() for box in boxes)
