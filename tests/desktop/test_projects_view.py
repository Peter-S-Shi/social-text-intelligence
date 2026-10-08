"""View models for the Projects surface."""

from __future__ import annotations

from datetime import UTC, datetime

from social_text_intelligence.application.model_provisioning import Readiness
from social_text_intelligence.application.project_workflow import (
    ProjectDetails,
    ProjectPhase,
)
from social_text_intelligence.application.projects import (
    ProjectStatus,
    ProjectSummary,
)
from social_text_intelligence.desktop.gate import AnalysisAvailability
from social_text_intelligence.desktop.projects import (
    NoticeKind,
    ProjectsActivity,
    ProjectsNotice,
    ProjectsState,
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
    assert "Analysed 3 rows · 1 rows failed" in view.facts
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
