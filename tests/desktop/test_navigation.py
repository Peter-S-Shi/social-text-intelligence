"""The fixed project-centred navigation, as a Qt-free view model."""

from __future__ import annotations

from social_text_intelligence.application.project_workflow import (
    ProjectDetails,
    ProjectPhase,
)
from social_text_intelligence.desktop.navigation import (
    PROJECT_SECTIONS,
    NavView,
    Section,
    build_navigation,
    default_section,
)
from social_text_intelligence.desktop.projects import (
    ProjectsActivity,
    ProjectsState,
)

from .test_projects_view import SUMMARY, details


def state_for(
    phase: ProjectPhase | None, activity: ProjectsActivity = ProjectsActivity.IDLE
) -> ProjectsState:
    current = None if phase is None else details(phase)
    return ProjectsState(current=current, listed=True, activity=activity)


def analysed(state_analysed: int, failed: int = 0) -> ProjectsState:
    current = details(
        ProjectPhase.ANALYZED,
        row_count=state_analysed + failed,
        analyzed_rows=state_analysed,
        failed_rows=failed,
    )
    return ProjectsState(current=current, listed=True)


def enabled(view: NavView) -> dict[Section, bool]:
    return {item.section: item.enabled for item in view.project_items}


def test_without_an_open_project_only_the_start_area_is_offered() -> None:
    view = build_navigation(state_for(None))

    assert view.project_title is None and view.project_items == ()
    assert [item.section for item in view.start_items] == [
        Section.PROJECTS,
        Section.ANALYZE,
    ]
    assert all(item.enabled for item in view.start_items)


def test_an_open_project_shows_the_six_fixed_pages_in_order() -> None:
    view = build_navigation(analysed(5))

    assert [item.section for item in view.project_items] == list(PROJECT_SECTIONS)
    assert [item.label for item in view.project_items] == [
        "Import & validation",
        "Results",
        "Review",
        "Agreement",
        "Insights · compare",
        "Insights · notes & cases",
    ]
    assert view.project_title == "Support tickets"


def test_before_analysis_only_import_and_validation_is_available_and_says_why() -> None:
    for phase in (ProjectPhase.NEEDS_COLUMN, ProjectPhase.READY):
        view = build_navigation(state_for(phase))

        flags = enabled(view)
        assert flags[Section.IMPORT] is True
        assert not any(flags[s] for s in PROJECT_SECTIONS if s is not Section.IMPORT)
        reasons = {item.section: item.reason for item in view.project_items}
        assert "Analyze the project first" in reasons[Section.RESULTS]
        assert reasons[Section.IMPORT] == ""


def test_an_analysed_project_opens_every_page() -> None:
    view = build_navigation(analysed(5, failed=1))

    assert all(enabled(view).values())
    badges = {item.section: item.badge for item in view.project_items}
    assert badges[Section.RESULTS] == "6"  # every row of the batch
    assert badges[Section.REVIEW] == "5"  # the rows that can be reviewed


def test_a_project_in_which_every_row_failed_has_results_but_nothing_to_review() -> (
    None
):
    view = build_navigation(analysed(0, failed=5))

    flags = enabled(view)
    assert flags[Section.RESULTS] is True and flags[Section.IMPORT] is True
    for section in (
        Section.REVIEW,
        Section.AGREEMENT,
        Section.COMPARE,
        Section.NOTES,
    ):
        assert flags[section] is False
    reasons = {item.section: item.reason for item in view.project_items}
    assert "nothing to review" in reasons[Section.REVIEW]


def test_the_start_area_waits_while_an_analysis_runs() -> None:
    view = build_navigation(state_for(ProjectPhase.READY, ProjectsActivity.ANALYZING))

    projects = next(i for i in view.start_items if i.section is Section.PROJECTS)
    assert projects.enabled is False
    assert "Cancel" in projects.reason  # the person is told how to leave
    analyze = next(i for i in view.start_items if i.section is Section.ANALYZE)
    assert analyze.enabled is True  # a page switch is harmless; the page waits


def test_the_page_a_project_opens_on_follows_how_far_it_has_come() -> None:
    assert default_section(details(ProjectPhase.NEEDS_COLUMN)) is Section.IMPORT
    assert default_section(details(ProjectPhase.READY)) is Section.IMPORT
    assert default_section(details(ProjectPhase.ANALYZED, analyzed_rows=3)) is (
        Section.RESULTS
    )
    assert default_section(ProjectDetails(SUMMARY, ProjectPhase.EMPTY)) is (
        Section.IMPORT
    )
