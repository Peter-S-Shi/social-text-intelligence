"""Review workflow for a presentation layer: open, judge, navigate, export.

A thin, typed seam over the shared review use cases. The review rules (what a valid
judgment is, which records are reviewable, agreement) stay in the review service, and
the stored human review stays separate from the immutable AI report. This module only
turns a project id into a read model, passes the human's draft through, and makes the
stale-write protection explicit: every save names the review the user was looking at.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from ..contracts import AnalysisReport, EmotionLabel, SentimentLabel
from ..contracts.errors import SocialTextIntelligenceError
from ..services.review import (
    MAX_REVIEW_NOTE_LENGTH,
    MIN_CONFIDENCE_COMPARISON_REVIEWS,
    ConfidenceBand,
    HumanReview,
    ReviewCase,
    ReviewFilter,
    ReviewJudgment,
    ReviewNavigation,
    ReviewSummary,
    filter_review_cases,
    review_cases,
    review_navigation,
    summarize_reviews,
)
from .project_workflow import ProjectBusyError, ProjectNotFoundError
from .projects import BatchWorkspace, ProjectRepository, WorkspaceMutationConflict
from .use_cases import ApplicationUseCases, ReviewConflict


class ReviewUnavailableError(SocialTextIntelligenceError):
    """The project has no analysed result, or the row is not a reviewable record."""

    def __init__(self) -> None:
        message = (
            "Only analysed rows can be reviewed. Rows that failed analysis, or "
            "projects that are not analysed yet, have nothing to review."
        )
        super().__init__(message)
        self.code = "review_unavailable"
        self.message = message


class ReviewConflictError(SocialTextIntelligenceError):
    """The record's review was saved elsewhere; the newer saved review was kept."""

    def __init__(self) -> None:
        message = (
            "This record's review was changed elsewhere. The newer saved review "
            "was kept and is shown now; your unsaved changes were not saved."
        )
        super().__init__(message)
        self.code = "review_conflict"
        self.message = message


class Advance(StrEnum):
    """Where to go after a successful save."""

    STAY = "stay"
    NEXT = "next"


@dataclass(frozen=True, slots=True)
class ReviewFilters:
    status: ReviewFilter = ReviewFilter.ALL
    sentiment: SentimentLabel | None = None  # filters on the AI label
    emotion: EmotionLabel | None = None  # filters on the AI dominant emotion

    def as_values(self) -> tuple[str, str, str]:
        return (
            self.status.value,
            self.sentiment.value if self.sentiment else "all",
            self.emotion.value if self.emotion else "all",
        )


@dataclass(frozen=True, slots=True)
class ReviewDraft:
    """What the human entered; the review service decides whether it is valid."""

    sentiment_judgment: ReviewJudgment | None = None
    human_sentiment: SentimentLabel | None = None
    emotion_judgment: ReviewJudgment | None = None
    human_dominant_emotion: EmotionLabel | None = None
    human_secondary_emotions: tuple[EmotionLabel, ...] = ()
    note: str = ""

    @classmethod
    def from_review(cls, review: HumanReview) -> ReviewDraft:
        return cls(
            sentiment_judgment=review.sentiment_judgment,
            human_sentiment=review.human_sentiment,
            emotion_judgment=review.emotion_judgment,
            human_dominant_emotion=review.human_dominant_emotion,
            human_secondary_emotions=review.human_secondary_emotions,
            note=review.note or "",
        )

    def as_values(self) -> dict[str, str]:
        return {
            "sentiment_judgment": _value(self.sentiment_judgment),
            "human_sentiment": _value(self.human_sentiment),
            "emotion_judgment": _value(self.emotion_judgment),
            "human_dominant_emotion": _value(self.human_dominant_emotion),
            "review_note": self.note,
        }


def _value(item: ReviewJudgment | SentimentLabel | EmotionLabel | None) -> str:
    return item.value if item is not None else ""


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """One reviewable row: the immutable AI report beside the human review."""

    row_number: int
    report: AnalysisReport
    review: HumanReview
    # The language tag exactly as the file supplied it (None if it gave none). It is
    # not the detected language, which lives in ``report.language``.
    supplied_language: str | None = None


EXCERPT_LENGTH = 90


@dataclass(frozen=True, slots=True)
class QueueEntry:
    """One line of the queue beside the open record: identity, a short text, status."""

    row_number: int
    record_id: str
    excerpt: str
    reviewed: bool


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) <= EXCERPT_LENGTH:
        return flat
    return flat[: EXCERPT_LENGTH - 1].rstrip() + "…"


@dataclass(frozen=True, slots=True)
class ReviewSnapshot:
    """The queue position and summary around one record (``record`` is ``None``
    only when the project has no reviewable rows at all)."""

    project_id: str
    filters: ReviewFilters
    record: ReviewRecord | None
    position: int
    queue_total: int
    filtered_count: int
    previous_row: int | None
    next_row: int | None
    next_unreviewed_row: int | None
    summary: ReviewSummary
    saved: ReviewRecord | None = None  # the record just saved, if this follows a save
    # The filtered queue in row order (always including the open record, so a record
    # that has just left the filter does not vanish from under the person).
    queue: tuple[QueueEntry, ...] = ()


class ReviewWorkflow:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository
        self._use_cases = ApplicationUseCases(repository, None)

    def open_review(
        self,
        project_id: str,
        filters: ReviewFilters = ReviewFilters(),  # noqa: B008 (frozen value)
        *,
        row: int | None = None,
    ) -> ReviewSnapshot:
        """The record at ``row`` (default: the first in the filtered queue)."""

        workspace = self._analysed(project_id)
        review_filter, sentiment_filter, emotion_filter = filters.as_values()
        if row is None:
            row = self._use_cases.review_index(
                project_id,
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
            )
        if row is None:  # an analysed project in which every row failed
            return self._empty(project_id, filters, workspace)
        details = self._use_cases.review_details(
            workspace,
            row,
            review_filter=review_filter,
            sentiment_filter=sentiment_filter,
            emotion_filter=emotion_filter,
        )
        if details is None:
            raise ReviewUnavailableError
        report = details.current.outcome.report
        assert report is not None
        cases = self._queue_cases(workspace, details.current, filters)
        navigation = self._navigation(workspace, details.current, cases)
        return ReviewSnapshot(
            project_id=project_id,
            filters=filters,
            record=ReviewRecord(
                row_number=details.current.outcome.prepared.row_number,
                report=report,
                review=details.current.review,
                supplied_language=details.current.outcome.prepared.supplied_language,
            ),
            position=details.position,
            queue_total=details.queue_total,
            filtered_count=details.filtered_count,
            previous_row=navigation.previous_row,
            next_row=navigation.next_row,
            next_unreviewed_row=navigation.next_unreviewed_row,
            summary=details.summary,
            queue=self._queue(cases),
        )

    def save(
        self,
        project_id: str,
        row: int,
        draft: ReviewDraft,
        *,
        expected: HumanReview,
        filters: ReviewFilters = ReviewFilters(),  # noqa: B008 (frozen value)
        advance: Advance = Advance.STAY,
    ) -> ReviewSnapshot:
        return self._save(project_id, row, "save", draft, expected, filters, advance)

    def accept_both(
        self,
        project_id: str,
        row: int,
        note: str,
        *,
        expected: HumanReview,
        filters: ReviewFilters = ReviewFilters(),  # noqa: B008 (frozen value)
        advance: Advance = Advance.STAY,
    ) -> ReviewSnapshot:
        return self._save(
            project_id,
            row,
            "accept_both",
            ReviewDraft(note=note),
            expected,
            filters,
            advance,
        )

    def agreement(self, project_id: str) -> ReviewSummary:
        """The project's agreement summary, whatever record is open (or none)."""

        workspace = self._analysed(project_id)
        assert workspace.result is not None and workspace.reviews is not None
        return summarize_reviews(workspace.result, workspace.reviews)

    def export_csv(self, project_id: str, *, include_native: bool = False) -> str:
        """The reviewed CSV exactly as the shared export defines it."""

        return self._use_cases.export_reviews(
            self._analysed(project_id), include_native=include_native
        )

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _queue_cases(
        workspace: BatchWorkspace, current: ReviewCase, filters: ReviewFilters
    ) -> tuple[ReviewCase, ...]:
        """The filtered queue, plus ``current`` even if it no longer matches.

        A record the person just saved can drop out of the active filter (for
        example "unreviewed"). Counting it as part of the queue keeps Next on the
        record after it, instead of wrapping back to the first match.
        """

        assert workspace.result is not None and workspace.reviews is not None
        review_filter, sentiment_filter, emotion_filter = filters.as_values()
        matching = {
            case.review.record_id
            for case in filter_review_cases(
                workspace.result,
                workspace.reviews,
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
            )
        }
        matching.add(current.review.record_id)
        return tuple(
            case
            for case in review_cases(workspace.result, workspace.reviews)
            if case.review.record_id in matching
        )

    @classmethod
    def _navigation(
        cls,
        workspace: BatchWorkspace,
        current: ReviewCase,
        queue: tuple[ReviewCase, ...],
    ) -> ReviewNavigation:
        """Previous and next around ``current``, even if it no longer matches."""

        assert workspace.result is not None and workspace.reviews is not None
        return review_navigation(
            workspace.result,
            workspace.reviews,
            current_record_id=current.review.record_id,
            filtered_cases=queue,
        )

    @staticmethod
    def _queue(queue: tuple[ReviewCase, ...]) -> tuple[QueueEntry, ...]:
        entries = []
        for case in queue:
            report = case.outcome.report
            assert report is not None  # only analysed rows are reviewable
            entries.append(
                QueueEntry(
                    row_number=case.outcome.prepared.row_number,
                    record_id=report.record.record_id,
                    excerpt=_excerpt(report.record.text),
                    reviewed=case.review.is_reviewed,
                )
            )
        return tuple(entries)

    def _analysed(self, project_id: str) -> BatchWorkspace:
        workspace = self._repository.get(project_id)
        if workspace is None:
            raise ProjectNotFoundError
        if workspace.result is None or workspace.reviews is None:
            raise ReviewUnavailableError
        return workspace

    def _empty(
        self, project_id: str, filters: ReviewFilters, workspace: BatchWorkspace
    ) -> ReviewSnapshot:
        assert workspace.result is not None and workspace.reviews is not None
        return ReviewSnapshot(
            project_id=project_id,
            filters=filters,
            record=None,
            position=0,
            queue_total=0,
            filtered_count=0,
            previous_row=None,
            next_row=None,
            next_unreviewed_row=None,
            summary=summarize_reviews(workspace.result, workspace.reviews),
        )

    def _save(
        self,
        project_id: str,
        row: int,
        action: str,
        draft: ReviewDraft,
        expected: HumanReview,
        filters: ReviewFilters,
        advance: Advance,
    ) -> ReviewSnapshot:
        review_filter, sentiment_filter, emotion_filter = filters.as_values()
        try:
            target = self._use_cases.save_review(
                project_id,
                row,
                action=action,
                values=draft.as_values(),
                secondary_emotions=[
                    label.value for label in draft.human_secondary_emotions
                ],
                review_filter=review_filter,
                sentiment_filter=sentiment_filter,
                emotion_filter=emotion_filter,
                expected=expected,
            )
        except ReviewConflict:
            raise ReviewConflictError from None
        except WorkspaceMutationConflict:
            raise ProjectBusyError from None
        if target is None:
            self._analysed(project_id)  # missing or not analysed: say which
            raise ReviewUnavailableError
        shown = self.open_review(project_id, filters, row=row)
        saved = shown.record
        if advance is Advance.NEXT and shown.next_row is not None:
            shown = self.open_review(project_id, filters, row=shown.next_row)
        return replace(shown, saved=saved)


__all__ = [
    "MAX_REVIEW_NOTE_LENGTH",
    "MIN_CONFIDENCE_COMPARISON_REVIEWS",
    "Advance",
    "ConfidenceBand",
    "HumanReview",
    "QueueEntry",
    "ReviewConflictError",
    "ReviewDraft",
    "ReviewFilter",
    "ReviewFilters",
    "ReviewJudgment",
    "ReviewRecord",
    "ReviewSnapshot",
    "ReviewSummary",
    "ReviewUnavailableError",
    "ReviewWorkflow",
]
