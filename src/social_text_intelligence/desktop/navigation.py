"""The fixed project-centred navigation, as a Qt-free view model.

The start window is the project list. One open project has six fixed pages (import and
validation, results, review, agreement, and the two insight views); a separate area
holds unsaved single-text analysis. A page that cannot be used yet is shown, disabled,
with the reason in words, so nothing is hidden and nothing silently does nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..application.project_workflow import ProjectDetails, ProjectPhase
from .projects import ProjectsActivity, ProjectsState
from .projects_view import row_view


class Section(StrEnum):
    PROJECTS = "projects"
    ANALYZE = "analyze"
    IMPORT = "import"
    RESULTS = "results"
    REVIEW = "review"
    AGREEMENT = "agreement"
    COMPARE = "compare"
    NOTES = "notes"


START_SECTIONS = (Section.PROJECTS, Section.ANALYZE)
PROJECT_SECTIONS = (
    Section.IMPORT,
    Section.RESULTS,
    Section.REVIEW,
    Section.AGREEMENT,
    Section.COMPARE,
    Section.NOTES,
)
LABELS = {
    Section.PROJECTS: "Projects",
    Section.ANALYZE: "Analyze one text",
    Section.IMPORT: "Import & validation",
    Section.RESULTS: "Results",
    Section.REVIEW: "Review",
    Section.AGREEMENT: "Agreement",
    Section.COMPARE: "Insights · compare",
    Section.NOTES: "Insights · notes & cases",
}
REVIEW_SECTIONS = (Section.REVIEW, Section.AGREEMENT, Section.COMPARE, Section.NOTES)
INSIGHT_SECTIONS = (Section.COMPARE, Section.NOTES)

NEEDS_ANALYSIS = "Analyze the project first."
NOTHING_ANALYSED = (
    "No row was analysed successfully, so there is nothing to review or compare."
)
WAIT_FOR_ANALYSIS = "An analysis is running. Cancel it to leave this project."


@dataclass(frozen=True, slots=True)
class NavItem:
    section: Section
    label: str
    enabled: bool = True
    reason: str = ""  # why a disabled page is disabled, in words
    badge: str = ""  # a count, when it helps


@dataclass(frozen=True, slots=True)
class NavView:
    project_title: str | None
    project_facts: str
    project_items: tuple[NavItem, ...]
    start_items: tuple[NavItem, ...]


def default_section(details: ProjectDetails) -> Section:
    """The page a project opens on: the results once there are results."""

    return Section.RESULTS if details.phase is ProjectPhase.ANALYZED else Section.IMPORT


def _project_items(details: ProjectDetails) -> tuple[NavItem, ...]:
    analysed = details.phase is ProjectPhase.ANALYZED
    reviewable = details.analyzed_rows or 0
    items = [NavItem(Section.IMPORT, LABELS[Section.IMPORT])]
    for section in PROJECT_SECTIONS[1:]:
        label = LABELS[section]
        if not analysed:
            items.append(NavItem(section, label, False, NEEDS_ANALYSIS))
        elif section is Section.RESULTS:
            items.append(NavItem(section, label, True, "", str(details.row_count)))
        elif reviewable == 0:
            items.append(NavItem(section, label, False, NOTHING_ANALYSED))
        else:
            badge = str(reviewable) if section is Section.REVIEW else ""
            items.append(NavItem(section, label, True, "", badge))
    return tuple(items)


def build_navigation(state: ProjectsState) -> NavView:
    analysing = state.activity is ProjectsActivity.ANALYZING
    start = (
        NavItem(
            Section.PROJECTS,
            LABELS[Section.PROJECTS],
            not analysing,
            WAIT_FOR_ANALYSIS if analysing else "",
        ),
        NavItem(Section.ANALYZE, LABELS[Section.ANALYZE]),
    )
    current = state.current
    if current is None:
        return NavView(None, "", (), start)
    facts = f"{current.row_count} rows" if current.row_count else ""
    return NavView(
        project_title=row_view(current.summary).title,
        project_facts=facts,
        project_items=_project_items(current),
        start_items=start,
    )
