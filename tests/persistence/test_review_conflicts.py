"""A human judgment is never silently overwritten by a stale save (real SQLite)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from social_text_intelligence.application.project_workflow import (
    CsvLimits,
    ProjectWorkflow,
)
from social_text_intelligence.application.projects import (
    BatchWorkspace,
    WorkspaceMutationConflict,
)
from social_text_intelligence.application.use_cases import (
    ApplicationUseCases,
    ReviewConflict,
)
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.sqlite_projects import (
    SqliteProjectRepository,
)
from social_text_intelligence.services.review import HumanReview, ReviewJudgment

from .workflow_samples import ScriptedGateway, csv_text

FILTERS = {
    "review_filter": "all",
    "sentiment_filter": "all",
    "emotion_filter": "all",
}
LIMITS = CsvLimits(max_bytes=20_000, max_rows=20, max_text_length=500)


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


def analysed_project(root: Path) -> str:
    flow = ProjectWorkflow(
        SqliteProjectRepository(AppDataLocations(root)), ScriptedGateway(), LIMITS
    )
    project_id = flow.import_csv(csv_text(3), name="P").summary.project_id
    flow.analyze(project_id)
    return project_id


def use_cases(root: Path) -> ApplicationUseCases:
    return ApplicationUseCases(
        SqliteProjectRepository(AppDataLocations(root)), ScriptedGateway()
    )


def review_of(root: Path, project_id: str, row: int) -> HumanReview:
    workspace = SqliteProjectRepository(AppDataLocations(root)).get(project_id)
    assert workspace is not None and workspace.reviews is not None
    assert workspace.result is not None
    identity = next(
        o.prepared.identity
        for o in workspace.result.outcomes
        if o.prepared.row_number == row
    )
    review = workspace.reviews.for_record(identity)
    assert review is not None
    return review


def judge(
    cases: ApplicationUseCases,
    project_id: str,
    row: int,
    sentiment: str,
    *,
    expected: HumanReview | None = None,
) -> int | None:
    return cases.save_review(
        project_id,
        row,
        action="save",
        values={
            "sentiment_judgment": "correct",
            "human_sentiment": sentiment,
            "emotion_judgment": "uncertain",
        },
        secondary_emotions=(),
        expected=expected,
        **FILTERS,
    )


def test_a_review_saved_elsewhere_inside_the_save_window_is_not_overwritten(
    tmp_path: Path,
) -> None:
    project_id = analysed_project(tmp_path)
    repository = RacingRepository(tmp_path)
    mine = ApplicationUseCases(repository, ScriptedGateway())
    theirs = use_cases(tmp_path)
    repository.before_mutate = lambda: judge(theirs, project_id, 1, "negative")

    with pytest.raises(ReviewConflict):
        judge(mine, project_id, 1, "positive")

    kept = review_of(tmp_path, project_id, 1)
    assert kept.human_sentiment is not None and kept.human_sentiment == "negative"
    assert kept.sentiment_judgment is ReviewJudgment.CORRECT


def test_a_form_opened_before_another_save_cannot_overwrite_it(
    tmp_path: Path,
) -> None:
    project_id = analysed_project(tmp_path)
    seen = review_of(tmp_path, project_id, 1)  # what my form was showing
    judge(use_cases(tmp_path), project_id, 1, "negative")  # saved elsewhere

    with pytest.raises(ReviewConflict):
        judge(use_cases(tmp_path), project_id, 1, "positive", expected=seen)

    kept = review_of(tmp_path, project_id, 1)
    assert kept.human_sentiment is not None and kept.human_sentiment == "negative"


def test_a_conflict_is_still_a_workspace_mutation_conflict() -> None:
    assert issubclass(ReviewConflict, WorkspaceMutationConflict)  # Flask maps to 409


def test_an_unchanged_review_and_other_records_do_not_conflict(
    tmp_path: Path,
) -> None:
    project_id = analysed_project(tmp_path)
    seen = review_of(tmp_path, project_id, 1)
    judge(use_cases(tmp_path), project_id, 2, "negative")  # a different record

    judge(use_cases(tmp_path), project_id, 1, "positive", expected=seen)

    assert review_of(tmp_path, project_id, 1).human_sentiment == "positive"
    assert review_of(tmp_path, project_id, 2).human_sentiment == "negative"
