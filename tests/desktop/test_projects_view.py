"""View models for the Projects surface."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from social_text_intelligence.application.model_provisioning import Readiness
from social_text_intelligence.application.project_workflow import (
    ProjectDetails,
    ProjectPhase,
)
from social_text_intelligence.application.projects import (
    ProjectStatus,
    ProjectSummary,
)
from social_text_intelligence.contracts.errors import ProjectStorageError
from social_text_intelligence.desktop.gate import AnalysisAvailability
from social_text_intelligence.desktop.projects import (
    NoticeKind,
    ProjectsActivity,
    ProjectsNotice,
    ProjectsState,
    notice_for,
)
from social_text_intelligence.desktop.projects_view import (
    build_detail_view,
    build_list_view,
    delete_confirmation,
)
from social_text_intelligence.services.batch import BatchProgress

from .fakes import status

AVAILABLE = AnalysisAvailability.AVAILABLE
SUMMARY = ProjectSummary(
    "ab" * 16,
    ProjectStatus.OK,
    "Support tickets",
    datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
    datetime(2026, 1, 3, 3, 4, tzinfo=UTC),
)


def details(phase: ProjectPhase, **extra: object) -> ProjectDetails:
    base: dict[str, object] = {
        "headers": ("record_id", "text"),
        "text_column": "text",
        "row_count": 5,
        "valid_rows": 4,
        "invalid_rows": 1,
    }
    base.update(extra)
    return ProjectDetails(SUMMARY, phase, **base)  # type: ignore[arg-type]


def test_empty_list_invites_an_import() -> None:
    view = build_list_view(ProjectsState(listed=True))
    assert view.rows == () and "Import a CSV" in view.summary
    assert view.import_enabled


def test_rows_distinguish_normal_unsupported_and_unreadable_projects() -> None:
    state = ProjectsState(
        projects=(
            SUMMARY,
            ProjectSummary("cd" * 16, ProjectStatus.UNSUPPORTED_VERSION),
            ProjectSummary("ef" * 16, ProjectStatus.UNREADABLE),
        ),
        listed=True,
    )
    normal, newer, junk = build_list_view(state).rows
    assert normal.title == "Support tickets" and normal.can_open
    assert "Updated" in normal.subtitle
    assert not newer.can_open and "newer version" in newer.title
    assert not junk.can_open and junk.title == "Unreadable project"
    assert "unreadable" in junk.accessible_name.lower()


def test_listing_failure_and_loading_are_said_plainly() -> None:
    assert (
        "could not be read"
        in build_list_view(ProjectsState(listed=True, list_failed=True)).summary
    )
    assert build_list_view(ProjectsState()).summary == "Loading projects…"


def test_actions_are_disabled_while_busy() -> None:
    view = build_list_view(ProjectsState(activity=ProjectsActivity.IMPORTING))
    assert not view.import_enabled and not view.row_actions_enabled


def test_column_step_shows_the_headers_and_no_analyze_yet() -> None:
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.NEEDS_COLUMN, headers=("a", "b"))),
        AVAILABLE,
        status(),
    )
    assert view is not None
    assert view.column_choices == ("a", "b") and not view.show_analyze
    assert "Choose which column" in view.state_line


def test_ready_project_offers_analyze_with_the_row_count() -> None:
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.READY)), AVAILABLE, status()
    )
    assert view is not None and view.show_analyze and view.analyze_enabled
    assert view.analyze_label == "Analyze 4 rows"
    assert view.facts == (
        "Text column: text",
        "5 rows · 4 ready · 1 with problems",
    )
    assert view.block is None


def test_analyze_is_blocked_with_a_visible_reason_when_models_are_not_ready() -> None:
    models = status(Readiness.READY, Readiness.INCOMPLETE)
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.READY)),
        AnalysisAvailability.MODELS_NOT_READY,
        models,
    )
    assert view is not None and not view.analyze_enabled
    assert view.block is not None and view.block.action.label == "Set up models…"


def test_h2_blocks_project_analysis_with_the_restart_text() -> None:
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.READY)),
        AnalysisAvailability.SESSION_BLOCKED,
        status(),
    )
    assert view is not None and not view.analyze_enabled
    assert view.block is not None and "restart" in view.block.body.lower()


def test_analyze_waits_for_another_analysis_to_finish() -> None:
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.READY)),
        AVAILABLE,
        status(),
        other_analysis_running=True,
    )
    assert view is not None and not view.analyze_enabled


def test_a_project_with_no_valid_rows_cannot_be_analysed() -> None:
    view = build_detail_view(
        ProjectsState(
            current=details(ProjectPhase.READY, valid_rows=0, invalid_rows=5)
        ),
        AVAILABLE,
        status(),
    )
    assert view is not None and not view.analyze_enabled


def test_progress_shows_the_row_and_cancel() -> None:
    state = ProjectsState(
        current=details(ProjectPhase.READY),
        activity=ProjectsActivity.ANALYZING,
        progress=BatchProgress(completed=3, total=8),
    )
    view = build_detail_view(state, AVAILABLE, status())
    assert view is not None and view.progress is not None
    assert view.progress.text == "Analyzing row 3 of 8"
    assert view.progress.fraction == 3 / 8 and view.progress.can_cancel
    assert not view.analyze_enabled and not view.delete_enabled


def test_before_the_first_row_says_the_models_are_loading() -> None:
    state = ProjectsState(
        current=details(ProjectPhase.READY), activity=ProjectsActivity.ANALYZING
    )
    view = build_detail_view(state, AVAILABLE, status())
    assert view is not None and view.progress is not None
    assert "Loading the models" in view.progress.text


def test_cancelling_says_nothing_will_be_saved_and_has_no_second_cancel() -> None:
    state = ProjectsState(
        current=details(ProjectPhase.READY),
        activity=ProjectsActivity.ANALYZING,
        progress=BatchProgress(2, 8),
        cancelling=True,
    )
    view = build_detail_view(state, AVAILABLE, status())
    assert view is not None and view.progress is not None
    assert "Nothing will be saved" in view.progress.text
    assert not view.progress.can_cancel


def test_an_analysed_project_shows_counts_and_cannot_be_re_analysed() -> None:
    done = details(
        ProjectPhase.ANALYZED,
        analyzed_rows=3,
        failed_rows=1,
        sentiment_counts=(("positive", 2), ("negative", 1), ("neutral", 0)),
    )
    view = build_detail_view(ProjectsState(current=done), AVAILABLE, status())
    assert view is not None and not view.show_analyze
    assert "Analysed 3 rows · 1 row failed" in view.facts
    assert "Sentiment: Positive 2 · Negative 1 · Neutral 0" in view.facts
    assert view.block is None  # nothing is blocked: there is nothing left to analyse


def test_the_notice_travels_with_the_view() -> None:
    notice = ProjectsNotice(NoticeKind.ERROR, "empty_file", "T", "B")
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.READY), notice=notice),
        AVAILABLE,
        status(),
    )
    assert view is not None and view.notice == notice


def test_no_project_open_means_no_detail_view() -> None:
    assert build_detail_view(ProjectsState(), AVAILABLE, status()) is None


def test_delete_wording_is_conservative() -> None:
    title, text = delete_confirmation("Support tickets")
    assert title == "Delete project"
    assert "removed from this application's data files" in text
    assert "backups are not affected" in text
    for forbidden in ("securely", "erase", "wipe", "shred", "permanently"):
        assert forbidden not in text.lower()


def test_the_csv_card_figures_and_recognised_metadata_columns() -> None:
    view = build_detail_view(
        ProjectsState(
            current=details(ProjectPhase.READY, headers=("record_id", "text", "topic"))
        ),
        AVAILABLE,
        status(),
    )

    assert view is not None
    assert (view.ready_count, view.rejected_count) == (4, 1)
    assert view.language_count is None  # the language check runs with the analysis
    present = {name: found for name, found in view.metadata}
    assert present["record_id"] and present["topic"]
    assert not present["community"] and not present["notes"]
    # the text column is not metadata, and nothing is inferred from other headers
    assert "text" not in present


def test_the_language_figure_appears_once_the_project_is_analysed() -> None:
    from social_text_intelligence.services.language import LanguageSummary

    done = details(
        ProjectPhase.ANALYZED,
        analyzed_rows=4,
        failed_rows=0,
        language=LanguageSummary(4, 2, 1, 1, 0, 0, (("fr", 1),)),
    )

    view = build_detail_view(ProjectsState(current=done), AVAILABLE, status())

    assert view is not None and view.language_count == 2  # unsupported + undetermined


def test_a_project_still_choosing_its_column_shows_no_figures() -> None:
    view = build_detail_view(
        ProjectsState(current=details(ProjectPhase.NEEDS_COLUMN)), AVAILABLE, status()
    )

    assert view is not None
    assert view.ready_count is None and view.rejected_count is None
    assert view.metadata == ()


def test_the_metadata_list_matches_the_batch_services_supported_fields() -> None:
    from social_text_intelligence.desktop.projects_view import METADATA_COLUMNS
    from social_text_intelligence.services.batch import SUPPORTED_BATCH_FIELDS

    assert METADATA_COLUMNS == SUPPORTED_BATCH_FIELDS


@pytest.mark.parametrize(
    ("code", "title"),
    [
        ("storage_full", "Not enough disk space"),
        ("storage_read_only", "The project can't be saved"),
        ("storage_locked", "The project file is in use"),
    ],
)
def test_storage_faults_keep_their_code_and_fixed_message_in_the_notice(
    code: str, title: str
) -> None:
    error = ProjectStorageError(code=code, message="Fixed advice. Nothing was changed.")

    notice = notice_for(error)

    assert (notice.code, notice.title) == (code, title)
    assert notice.body == "Fixed advice. Nothing was changed."
    assert notice.kind is NoticeKind.ERROR


def counted(
    name: str,
    *,
    rows: int | None,
    rejected: int = 0,
    analysed: int = 0,
    reviewed: int = 0,
    corrected: int = 0,
    key: str = "ab",
) -> ProjectSummary:
    return ProjectSummary(
        key * 16,
        ProjectStatus.OK,
        name,
        datetime(2026, 1, 2, tzinfo=UTC),
        datetime(2026, 1, 3, tzinfo=UTC),
        row_count=rows,
        rejected_rows=rejected,
        analysed_rows=analysed,
        reviewed_rows=reviewed,
        corrected_rows=corrected,
    )


def test_a_row_states_its_size_and_its_review_progress() -> None:
    state = ProjectsState(
        projects=(
            counted(
                "Checkout", rows=48, rejected=1, analysed=46, reviewed=29, corrected=10
            ),
        ),
        listed=True,
    )

    (row,) = build_list_view(state).rows

    assert row.rows_line == "48 rows · 1 rejected at import"
    assert row.review_state == "in_review"
    assert row.review_fraction == 29 / 46
    assert row.review_line == "29 / 46 reviewed · 10 corrected"
    assert "29 / 46 reviewed" in row.accessible_name


def test_review_states_cover_every_project() -> None:
    state = ProjectsState(
        projects=(
            counted("Fresh", rows=5, key="aa"),
            counted("Half", rows=5, analysed=5, reviewed=2, corrected=0, key="bb"),
            counted("Done", rows=5, analysed=5, reviewed=5, corrected=1, key="cc"),
            counted("Nothing ok", rows=5, analysed=0, key="dd"),
            counted("Empty import", rows=0, key="ee"),
        ),
        listed=True,
    )

    rows = {r.title: r for r in build_list_view(state).rows}

    assert rows["Fresh"].review_state == "not_analysed"
    assert rows["Fresh"].review_line == "Not analysed yet"
    assert rows["Half"].review_state == "in_review"
    assert rows["Done"].review_state == "fully_reviewed"
    assert rows["Done"].review_fraction == 1.0
    assert rows["Nothing ok"].review_state == "not_analysed"
    assert rows["Empty import"].rows_line == "No rows imported"


def test_a_project_without_counts_shows_no_progress_and_no_state() -> None:
    state = ProjectsState(
        projects=(SUMMARY,), listed=True
    )  # a repository with no counts

    (row,) = build_list_view(state).rows

    assert row.review_state == "unknown" and row.rows_line == ""
    assert row.review_line == ""


def test_the_review_tabs_count_and_filter_the_projects() -> None:
    state = ProjectsState(
        projects=(
            counted("Fresh", rows=5, key="aa"),
            counted("Half", rows=5, analysed=5, reviewed=2, corrected=0, key="bb"),
            counted("Done", rows=5, analysed=5, reviewed=5, corrected=1, key="cc"),
            ProjectSummary("dd" * 16, ProjectStatus.UNREADABLE),
        ),
        listed=True,
    )

    everything = build_list_view(state)
    assert [(t, v, n) for t, v, n in everything.tabs] == [
        ("All", "all", 4),
        ("Not analysed", "not_analysed", 1),
        ("In review", "in_review", 1),
        ("Fully reviewed", "fully_reviewed", 1),
    ]
    assert len(everything.rows) == 4  # an unreadable entry is always listed under All

    half = build_list_view(state, review_filter="in_review")
    assert [r.title for r in half.rows] == ["Half"]
    assert half.selected_filter == "in_review"
    assert half.summary.startswith("1 of 4")


def test_a_filter_that_matches_nothing_says_so_and_keeps_the_tabs() -> None:
    state = ProjectsState(projects=(counted("Fresh", rows=5),), listed=True)

    view = build_list_view(state, review_filter="fully_reviewed")

    assert view.rows == () and "No projects match" in view.summary
    assert view.tabs[0][2] == 1


def test_a_project_whose_analysis_produced_no_result_is_not_called_unanalysed() -> None:
    summary = ProjectSummary(
        "ab" * 16,
        ProjectStatus.OK,
        "All failed",
        row_count=3,
        rejected_rows=0,
        analysed_rows=0,
        attempted_rows=3,
        reviewed_rows=0,
        corrected_rows=0,
    )

    (row,) = build_list_view(ProjectsState(projects=(summary,), listed=True)).rows

    assert row.review_line == "Analysis ran · no row succeeded"
    assert row.review_state == "not_analysed"
