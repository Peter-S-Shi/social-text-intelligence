"""Case preparation, sessions, comparison, summaries, and export for M9."""

from __future__ import annotations

import csv
import io
import random
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from secrets import token_urlsafe
from typing import TypeVar

from ..contracts import (
    AmbiguityLevel,
    CaseAttempt,
    CaseDifficulty,
    CaseOrderMode,
    ComparisonState,
    ContextNoteSnapshot,
    EmotionSignalSnapshot,
    EscalationReason,
    FeedbackTiming,
    FrozenTrainingCase,
    HumanReviewSnapshot,
    LearningObjective,
    MockModerationRecommendation,
    ModerationCaseSource,
    ModerationDisposition,
    ModerationJudgment,
    ModerationSeverity,
    ModerationTrainingCase,
    ModerationTrainingSession,
    ReferenceDecision,
    ReferenceProvenance,
    SentimentSignalSnapshot,
    SourceRecordSnapshot,
    TraineeDecision,
    TrainingMode,
    TrainingSessionStatus,
    UnclearReason,
    ViolationCategory,
)
from ..contracts.errors import ValidationError
from .batch import BatchResult, safe_spreadsheet_text
from .insights import (
    INSUFFICIENT_SAMPLE_BELOW,
    SMALL_SAMPLE_BELOW,
    ContextAssociation,
    InsightState,
    SampleSizeAssessment,
    sample_size_assessment,
)
from .review import ReviewState

DEFAULT_MAX_PREPARED_CASES = 100
DEFAULT_MAX_SESSION_CASES = 50
DEFAULT_MAX_SESSION_ATTEMPTS = 20
MAX_CUSTOM_CASE_TEXT = 20_000
EnumValue = TypeVar("EnumValue", bound=StrEnum)

TRUSTED_METADATA_FIELDS = (
    "source_type",
    "source_label",
    "language",
    "timestamp",
    "topic",
    "community",
    "parent_record_id",
    "notes",
)


@dataclass(frozen=True, slots=True)
class ModerationWorkspace:
    source_batch_token: str | None = None
    prepared_cases: tuple[ModerationTrainingCase, ...] = ()
    sessions: tuple[ModerationTrainingSession, ...] = ()
    active_session_id: str | None = None

    def session(self, session_id: str) -> ModerationTrainingSession | None:
        return next(
            (item for item in self.sessions if item.session_id == session_id),
            None,
        )


@dataclass(frozen=True, slots=True)
class ModerationLimits:
    max_prepared_cases: int = DEFAULT_MAX_PREPARED_CASES
    max_session_cases: int = DEFAULT_MAX_SESSION_CASES
    max_session_attempts: int = DEFAULT_MAX_SESSION_ATTEMPTS

    def __post_init__(self) -> None:
        if (
            self.max_prepared_cases < 1
            or self.max_session_cases < 1
            or self.max_session_attempts < 1
        ):
            raise ValueError("Moderation workspace limits must be positive.")


@dataclass(frozen=True, slots=True)
class CaseFilter:
    category: ViolationCategory | None = None
    difficulty: CaseDifficulty | None = None
    ambiguity: AmbiguityLevel | None = None
    learning_objective: LearningObjective | None = None
    safety_sensitive: bool | None = None


@dataclass(frozen=True, slots=True)
class FieldComparison:
    field: str
    first: ComparisonState
    final: ComparisonState
    trainee_first: str
    trainee_final: str
    reference: str


@dataclass(frozen=True, slots=True)
class CaseComparison:
    case_id: str
    fields: tuple[FieldComparison, ...]
    first_overall: ComparisonState
    final_overall: ComparisonState
    first_guidance_warnings: tuple[str, ...]
    final_guidance_warnings: tuple[str, ...]
    educational_flags: tuple[str, ...]
    reference_provenance: ReferenceProvenance | None


@dataclass(frozen=True, slots=True)
class SummaryMetric:
    name: str
    numerator: int
    denominator: int
    excluded: int
    sample: SampleSizeAssessment

    @property
    def rate(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0


@dataclass(frozen=True, slots=True)
class CategorySummary:
    category: ViolationCategory
    exact_or_acceptable: int
    denominator: int
    sample: SampleSizeAssessment


@dataclass(frozen=True, slots=True)
class SeveritySummary:
    severity: ModerationSeverity
    exact_or_acceptable: int
    denominator: int
    sample: SampleSizeAssessment


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    total_cases: int
    completed_cases: int
    unscored_cases: int
    ai_available_cases: int
    first_metrics: tuple[SummaryMetric, ...]
    final_metrics: tuple[SummaryMetric, ...]
    acceptable_alternative_count: int
    acceptable_alternative_alignment: SummaryMetric
    trainee_ai_agreement: SummaryMetric
    ai_reference_alignment: SummaryMetric
    categories: tuple[CategorySummary, ...]
    severities: tuple[SeveritySummary, ...]
    reference_provenance_counts: tuple[tuple[ReferenceProvenance, int], ...]
    educational_flag_counts: tuple[tuple[str, int], ...]


def _parse_enum(
    enum_type: type[EnumValue], value: str, *, field: str
) -> EnumValue:
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_choice",
            message=f"Select a supported {field}.",
        ) from error


def parse_moderation_judgment(
    *,
    disposition: str,
    primary_violation: str,
    secondary_violations: Sequence[str],
    severity: str,
    escalate: bool,
    escalation_reason: str,
    unclear_reasons: Sequence[str],
) -> ModerationJudgment:
    if not disposition:
        raise ValidationError(
            field="disposition",
            code="required",
            message="Disposition is required.",
        )
    if not primary_violation:
        raise ValidationError(
            field="primary_violation",
            code="required",
            message="Primary violation or No violation is required.",
        )
    if not severity:
        raise ValidationError(
            field="severity",
            code="required",
            message="Severity is required.",
        )
    return ModerationJudgment(
        disposition=_parse_enum(
            ModerationDisposition, disposition, field="disposition"
        ),
        primary_violation=_parse_enum(
            ViolationCategory,
            primary_violation,
            field="primary_violation",
        ),
        secondary_violations=tuple(
            _parse_enum(
                ViolationCategory, item, field="secondary_violations"
            )
            for item in secondary_violations
        ),
        severity=_parse_enum(
            ModerationSeverity, severity, field="severity"
        ),
        escalate=escalate,
        escalation_reason=(
            _parse_enum(
                EscalationReason,
                escalation_reason,
                field="escalation_reason",
            )
            if escalation_reason
            else None
        ),
        unclear_reasons=tuple(
            _parse_enum(UnclearReason, item, field="unclear_reasons")
            for item in unclear_reasons
        ),
    )


def parse_trainee_decision(
    *,
    disposition: str,
    primary_violation: str,
    secondary_violations: Sequence[str],
    severity: str,
    escalate: bool,
    escalation_reason: str,
    unclear_reasons: Sequence[str],
    reasoning: str,
    reviewer_note: str,
) -> TraineeDecision:
    return TraineeDecision.create(
        parse_moderation_judgment(
            disposition=disposition,
            primary_violation=primary_violation,
            secondary_violations=secondary_violations,
            severity=severity,
            escalate=escalate,
            escalation_reason=escalation_reason,
            unclear_reasons=unclear_reasons,
        ),
        reasoning=reasoning,
        reviewer_note=reviewer_note,
    )


def filter_training_cases(
    cases: Sequence[ModerationTrainingCase], filters: CaseFilter
) -> tuple[ModerationTrainingCase, ...]:
    return tuple(
        case
        for case in cases
        if (
            filters.category is None
            or filters.category in case.categories_involved
        )
        and (
            filters.difficulty is None
            or case.difficulty is filters.difficulty
        )
        and (
            filters.ambiguity is None
            or case.ambiguity_level is filters.ambiguity
        )
        and (
            filters.learning_objective is None
            or case.learning_objective is filters.learning_objective
        )
        and (
            filters.safety_sensitive is None
            or case.safety_sensitive is filters.safety_sensitive
        )
    )


def _snapshot_context_notes(
    insight_state: InsightState,
    *,
    record_id: str,
    topic: str,
    community: str,
    source_label: str,
) -> tuple[ContextNoteSnapshot, ...]:
    matches: list[ContextNoteSnapshot] = []
    for note in insight_state.notes:
        applies = (
            note.association is ContextAssociation.RECORD
            and note.association_value == record_id
        ) or (
            note.association is ContextAssociation.TOPIC
            and note.association_value == topic
        ) or (
            note.association is ContextAssociation.COMMUNITY
            and note.association_value == community
        ) or (
            note.association is ContextAssociation.SOURCE_LABEL
            and note.association_value == source_label
        )
        if applies:
            matches.append(
                ContextNoteSnapshot(
                    association=note.association.value,
                    association_value=note.association_value,
                    phrase=note.phrase,
                    explanation=note.explanation,
                    context_importance=note.context_importance,
                    tags=tuple(tag.value for tag in note.tags),
                    created_at=note.created_at,
                )
            )
    return tuple(matches)


def prepare_workspace_case(
    workspace: ModerationWorkspace,
    result: BatchResult,
    reviews: ReviewState,
    insights: InsightState,
    *,
    record_id: str,
    excerpt: str,
    difficulty: CaseDifficulty,
    learning_objective: LearningObjective,
    reference: ReferenceDecision | None,
    mock_recommendation: MockModerationRecommendation | None,
    policy_id: str,
    policy_version: str,
    valid_policy_clause_ids: Sequence[str],
    limits: ModerationLimits,
    case_id_factory: Callable[[], str] = lambda: token_urlsafe(10),
) -> ModerationWorkspace:
    if len(workspace.prepared_cases) >= limits.max_prepared_cases:
        raise ValidationError(
            field="prepared_cases",
            code="prepared_case_limit",
            message=(
                f"This temporary workspace allows at most "
                f"{limits.max_prepared_cases} prepared cases. Export or "
                "explicitly clear cases, or wait for expiry."
            ),
        )
    outcome = next(
        (
            item
            for item in result.outcomes
            if item.report is not None
            and item.prepared.identity == record_id
        ),
        None,
    )
    if outcome is None or outcome.report is None:
        raise ValidationError(
            field="record_id",
            code="not_eligible",
            message="Only successfully analyzed records can become training cases.",
        )
    report = outcome.report
    source_text = report.record.text
    normalized_excerpt = unicodedata.normalize(
        "NFC", excerpt.replace("\r\n", "\n").replace("\r", "\n")
    ).strip()
    if normalized_excerpt:
        if (
            len(normalized_excerpt) > MAX_CUSTOM_CASE_TEXT
            or normalized_excerpt not in source_text
        ):
            raise ValidationError(
                field="excerpt",
                code="invalid_excerpt",
                message=(
                    "A training excerpt must be a literal bounded excerpt of the "
                    "source record."
                ),
            )
        case_text = normalized_excerpt
        excerpted = normalized_excerpt != source_text
    else:
        case_text = source_text
        excerpted = False
    if (
        reference is not None
        and reference.provenance is not ReferenceProvenance.SELF_AUTHORED
    ):
        raise ValidationError(
            field="reference_provenance",
            code="invalid_reference_provenance",
            message=(
                "References prepared in this single-user workflow must be marked "
                "self-authored."
            ),
        )
    if reference is not None and not set(reference.policy_clause_ids) <= set(
        valid_policy_clause_ids
    ):
        raise ValidationError(
            field="policy_clause_ids",
            code="unknown_clause",
            message="A self-authored reference contains an unknown policy clause.",
        )
    review = reviews.for_record(record_id)
    review_snapshot = None
    if review is not None:
        review_snapshot = HumanReviewSnapshot(
            status="reviewed" if review.is_reviewed else "unreviewed",
            sentiment_judgment=(
                review.sentiment_judgment.value
                if review.sentiment_judgment
                else ""
            ),
            human_sentiment=(
                review.human_sentiment.value if review.human_sentiment else ""
            ),
            emotion_judgment=(
                review.emotion_judgment.value
                if review.emotion_judgment
                else ""
            ),
            human_dominant_emotion=(
                review.human_dominant_emotion.value
                if review.human_dominant_emotion
                else ""
            ),
            human_secondary_emotions=tuple(
                item.value for item in review.human_secondary_emotions
            ),
        )
    record = report.record
    metadata_values = {
        "source_type": record.source_type.value,
        "source_label": record.source_label or "",
        "language": record.language or "",
        "timestamp": record.timestamp.isoformat() if record.timestamp else "",
        "topic": record.topic or "",
        "community": record.community or "",
        "parent_record_id": record.parent_record_id or "",
        "notes": record.notes or "",
    }
    snapshot = SourceRecordSnapshot(
        source_record_id=record.record_id,
        text=source_text,
        excerpted=excerpted,
        excerpt_provenance=(
            "literal_user_selected_excerpt"
            if excerpted
            else "complete_source_record"
        ),
        trusted_metadata=tuple(
            (field, metadata_values[field]) for field in TRUSTED_METADATA_FIELDS
        ),
        sentiment=SentimentSignalSnapshot(
            label=report.sentiment.label.value,
            confidence=report.sentiment.confidence,
            model_name=report.sentiment.provider.model_name,
            revision=report.sentiment.provider.revision,
        ),
        emotion=EmotionSignalSnapshot(
            dominant_emotion=report.emotion.dominant_emotion.value,
            secondary_emotions=tuple(
                item.value for item in report.emotion.secondary_emotions
            ),
            confidence=report.emotion.confidence,
            threshold=report.emotion.threshold,
            model_name=report.emotion.provider.model_name,
            revision=report.emotion.provider.revision,
        ),
        human_review=review_snapshot,
        context_notes=_snapshot_context_notes(
            insights,
            record_id=record.record_id,
            topic=record.topic or "",
            community=record.community or "",
            source_label=record.source_label or "",
        ),
    )
    case_id = f"workspace-{case_id_factory()}"
    prepared = ModerationTrainingCase(
        case_id=case_id,
        fixture_version="workspace-snapshot-v1",
        source=ModerationCaseSource.WORKSPACE_RECORD,
        policy_id=policy_id,
        policy_version=policy_version,
        difficulty=difficulty,
        topic=record.topic or "workspace record",
        categories_involved=(
            (
                reference.preferred.primary_violation,
                *reference.preferred.secondary_violations,
            )
            if reference is not None
            and reference.preferred.primary_violation
            is not ViolationCategory.NO_VIOLATION
            else ()
        ),
        context_available=bool(snapshot.context_notes),
        ambiguity_level=AmbiguityLevel.MEDIUM,
        safety_sensitive=bool(
            reference is not None
            and (
                reference.preferred.severity
                in (ModerationSeverity.HIGH, ModerationSeverity.CRITICAL)
                or reference.preferred.escalate
            )
        ),
        learning_objective=learning_objective,
        text=case_text,
        context="User-prepared temporary workspace case.",
        reference=reference,
        mock_recommendation=mock_recommendation,
        source_snapshot=snapshot,
        original_order=len(workspace.prepared_cases) + 10_000,
    )
    return replace(
        workspace, prepared_cases=(*workspace.prepared_cases, prepared)
    )


def clear_prepared_cases(
    workspace: ModerationWorkspace,
) -> ModerationWorkspace:
    if workspace.active_session_id is not None:
        raise ValidationError(
            field="active_session",
            code="active_session",
            message="Cancel or complete the active session before clearing cases.",
        )
    return replace(workspace, prepared_cases=())


def _case_categories(case: ModerationTrainingCase) -> tuple[str, ...]:
    if case.categories_involved:
        return tuple(item.value for item in case.categories_involved)
    return ("no_violation",)


def _balanced_sample(
    cases: Sequence[ModerationTrainingCase],
    count: int,
    *,
    rng: random.Random,
) -> tuple[ModerationTrainingCase, ...]:
    remaining = list(cases)
    selected: list[ModerationTrainingCase] = []
    difficulty_counts: Counter[CaseDifficulty] = Counter()
    category_counts: Counter[str] = Counter()
    while remaining and len(selected) < count:
        rng.shuffle(remaining)
        chosen = min(
            remaining,
            key=lambda case: (
                difficulty_counts[case.difficulty],
                min(category_counts[item] for item in _case_categories(case)),
                case.original_order,
            ),
        )
        remaining.remove(chosen)
        selected.append(chosen)
        difficulty_counts[chosen.difficulty] += 1
        category_counts.update(_case_categories(chosen))
    return tuple(selected)


def _imbalance_note(
    pool: Sequence[ModerationTrainingCase],
    selected: Sequence[ModerationTrainingCase],
) -> str:
    pool_difficulties = {item.difficulty for item in pool}
    selected_difficulties = {item.difficulty for item in selected}
    pool_categories = {
        category for item in pool for category in _case_categories(item)
    }
    selected_categories = {
        category for item in selected for category in _case_categories(item)
    }
    missing_difficulties = pool_difficulties - selected_difficulties
    missing_categories = pool_categories - selected_categories
    if not missing_difficulties and not missing_categories:
        return ""
    return (
        "Perfect balance was not possible at the selected size; "
        f"{len(missing_difficulties)} difficulty bands and "
        f"{len(missing_categories)} category groups from the pool are absent."
    )


def start_training_session(
    workspace: ModerationWorkspace,
    available_cases: Sequence[ModerationTrainingCase],
    *,
    case_ids: Sequence[str],
    case_count: int,
    mode: TrainingMode,
    feedback_timing: FeedbackTiming,
    order_mode: CaseOrderMode,
    content_notice_confirmed: bool,
    limits: ModerationLimits,
    random_seed: int = 0,
    session_id_factory: Callable[[], str] = lambda: token_urlsafe(10),
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ModerationWorkspace:
    if workspace.active_session_id is not None:
        raise ValidationError(
            field="active_session",
            code="active_session",
            message="Continue or cancel the active training session first.",
        )
    if len(workspace.sessions) >= limits.max_session_attempts:
        raise ValidationError(
            field="sessions",
            code="session_attempt_limit",
            message=(
                f"This temporary workspace retains at most "
                f"{limits.max_session_attempts} session attempts. Export or "
                "explicitly clear the workspace, or wait for expiry."
            ),
        )
    if case_count < 1 or case_count > limits.max_session_cases:
        raise ValidationError(
            field="case_count",
            code="invalid_case_count",
            message=(
                f"A session must contain between 1 and "
                f"{limits.max_session_cases} cases."
            ),
        )
    by_id = {case.case_id: case for case in available_cases}
    if len(case_ids) != len(set(case_ids)):
        raise ValidationError(
            field="case_ids",
            code="duplicate_case",
            message="Explicitly selected cases must be unique.",
        )
    if case_ids:
        try:
            selected = tuple(by_id[item] for item in case_ids)
        except KeyError as error:
            raise ValidationError(
                field="case_ids",
                code="unknown_case",
                message="A selected case is not available.",
            ) from error
        if len(selected) > limits.max_session_cases:
            raise ValidationError(
                field="case_ids",
                code="session_case_limit",
                message=(
                    f"A session may contain at most "
                    f"{limits.max_session_cases} cases."
                ),
            )
    else:
        if case_count > len(available_cases):
            raise ValidationError(
                field="case_count",
                code="insufficient_cases",
                message="The filtered pool does not contain enough cases.",
            )
        selected = _balanced_sample(
            available_cases, case_count, rng=random.Random(random_seed)
        )
    if any(item.safety_sensitive for item in selected) and not (
        content_notice_confirmed
    ):
        raise ValidationError(
            field="content_notice",
            code="content_notice_required",
            message="Confirm the concise sensitive-content notice to start.",
        )
    if order_mode is CaseOrderMode.RANDOM:
        ordered = list(selected)
        random.Random(random_seed).shuffle(ordered)
        selected = tuple(ordered)
    elif order_mode is CaseOrderMode.DIFFICULTY_PROGRESSION:
        rank = {
            CaseDifficulty.BEGINNER: 0,
            CaseDifficulty.INTERMEDIATE: 1,
            CaseDifficulty.ADVANCED: 2,
        }
        selected = tuple(
            sorted(
                selected,
                key=lambda item: (rank[item.difficulty], item.original_order),
            )
        )
    else:
        selected = tuple(sorted(selected, key=lambda item: item.original_order))
    frozen = tuple(
        FrozenTrainingCase(
            case=case,
            frozen_reference=case.reference,
            frozen_policy_id=case.policy_id,
            frozen_policy_version=case.policy_version,
            frozen_clause_ids=(
                case.reference.policy_clause_ids if case.reference else ()
            ),
        )
        for case in selected
    )
    session = ModerationTrainingSession(
        session_id=session_id_factory(),
        cases=frozen,
        mode=mode,
        feedback_timing=feedback_timing,
        order_mode=order_mode,
        attempts=(),
        status=TrainingSessionStatus.ACTIVE,
        created_at=now(),
        imbalance_note=_imbalance_note(available_cases, selected),
    )
    return replace(
        workspace,
        sessions=(*workspace.sessions, session),
        active_session_id=session.session_id,
    )


def _replace_session(
    workspace: ModerationWorkspace, updated: ModerationTrainingSession
) -> ModerationWorkspace:
    if workspace.session(updated.session_id) is None:
        raise ValidationError(
            field="session_id",
            code="missing_session",
            message="Training session not found.",
        )
    return replace(
        workspace,
        sessions=tuple(
            updated if item.session_id == updated.session_id else item
            for item in workspace.sessions
        ),
        active_session_id=(
            updated.session_id
            if updated.status is TrainingSessionStatus.ACTIVE
            else (
                None
                if workspace.active_session_id == updated.session_id
                else workspace.active_session_id
            )
        ),
    )


def submit_first_decision(
    workspace: ModerationWorkspace,
    *,
    session_id: str,
    case_id: str,
    decision: TraineeDecision,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ModerationWorkspace:
    session = workspace.session(session_id)
    if session is None:
        raise ValidationError(
            field="session_id",
            code="missing_session",
            message="Training session not found.",
        )
    if case_id not in {item.case.case_id for item in session.cases}:
        raise ValidationError(
            field="case_id",
            code="unknown_case",
            message="The case is not part of this session.",
        )
    if any(item.case_id == case_id for item in session.attempts):
        raise ValidationError(
            field="case_id",
            code="duplicate_submission",
            message="The first decision for this case was already submitted.",
        )
    if session.status is not TrainingSessionStatus.ACTIVE:
        raise ValidationError(
            field="session_id",
            code="missing_active_session",
            message="An active training session is required.",
        )
    timestamp = now()
    attempt = CaseAttempt(
        case_id=case_id,
        first_decision=decision,
        final_decision=decision,
        first_submitted_at=timestamp,
        final_submitted_at=timestamp,
    )
    attempts = (*session.attempts, attempt)
    complete = len(attempts) == len(session.cases)
    updated = replace(
        session,
        attempts=attempts,
        status=(
            TrainingSessionStatus.COMPLETED
            if complete
            else TrainingSessionStatus.ACTIVE
        ),
        completed_at=timestamp if complete else None,
    )
    return _replace_session(workspace, updated)


def feedback_available(
    session: ModerationTrainingSession, case_id: str
) -> bool:
    return (
        session.feedback_timing is FeedbackTiming.IMMEDIATE
        or session.status
        in (TrainingSessionStatus.COMPLETED, TrainingSessionStatus.CANCELLED)
    ) and any(item.case_id == case_id for item in session.attempts)


def mark_feedback_viewed(
    workspace: ModerationWorkspace, *, session_id: str, case_id: str
) -> ModerationWorkspace:
    session = workspace.session(session_id)
    if session is None or not feedback_available(session, case_id):
        raise ValidationError(
            field="feedback",
            code="feedback_unavailable",
            message="Feedback is not available for this case yet.",
        )
    found = False
    attempts: list[CaseAttempt] = []
    for attempt in session.attempts:
        if attempt.case_id == case_id:
            found = True
            attempts.append(replace(attempt, feedback_viewed=True))
        else:
            attempts.append(attempt)
    if not found:
        raise ValidationError(
            field="case_id",
            code="missing_attempt",
            message="Submit a decision before viewing feedback.",
        )
    return _replace_session(
        workspace, replace(session, attempts=tuple(attempts))
    )


def revise_final_decision(
    workspace: ModerationWorkspace,
    *,
    session_id: str,
    case_id: str,
    decision: TraineeDecision,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ModerationWorkspace:
    session = workspace.session(session_id)
    if session is None:
        raise ValidationError(
            field="session_id",
            code="missing_session",
            message="Training session not found.",
        )
    changed = False
    attempts: list[CaseAttempt] = []
    for attempt in session.attempts:
        if attempt.case_id != case_id:
            attempts.append(attempt)
            continue
        if not attempt.feedback_viewed:
            raise ValidationError(
                field="feedback",
                code="feedback_required",
                message="View available feedback before revising a decision.",
            )
        if attempt.final_decision == decision:
            raise ValidationError(
                field="decision",
                code="duplicate_revision",
                message="The revised decision is unchanged.",
            )
        changed = True
        attempts.append(
            replace(
                attempt,
                final_decision=decision,
                final_submitted_at=now(),
                revision_count=attempt.revision_count + 1,
            )
        )
    if not changed:
        raise ValidationError(
            field="case_id",
            code="missing_attempt",
            message="No submitted attempt exists for this case.",
        )
    return _replace_session(
        workspace, replace(session, attempts=tuple(attempts))
    )


def cancel_session(
    workspace: ModerationWorkspace,
    *,
    session_id: str,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ModerationWorkspace:
    session = workspace.session(session_id)
    if session is None or session.status is not TrainingSessionStatus.ACTIVE:
        raise ValidationError(
            field="session_id",
            code="missing_active_session",
            message="Only the active session can be cancelled.",
        )
    return _replace_session(
        workspace,
        replace(
            session,
            status=TrainingSessionStatus.CANCELLED,
            cancelled_at=now(),
        ),
    )


def restart_session(
    workspace: ModerationWorkspace,
    *,
    session_id: str,
    limits: ModerationLimits,
    session_id_factory: Callable[[], str] = lambda: token_urlsafe(10),
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ModerationWorkspace:
    previous = workspace.session(session_id)
    if previous is None:
        raise ValidationError(
            field="session_id",
            code="missing_session",
            message="Training session not found.",
        )
    if workspace.active_session_id is not None:
        raise ValidationError(
            field="active_session",
            code="active_session",
            message="Cancel or complete the active session before restarting.",
        )
    if len(workspace.sessions) >= limits.max_session_attempts:
        raise ValidationError(
            field="sessions",
            code="session_attempt_limit",
            message=(
                f"This temporary workspace retains at most "
                f"{limits.max_session_attempts} session attempts."
            ),
        )
    restarted = replace(
        previous,
        session_id=session_id_factory(),
        attempts=(),
        status=TrainingSessionStatus.ACTIVE,
        created_at=now(),
        cancelled_at=None,
        completed_at=None,
    )
    return replace(
        workspace,
        sessions=(*workspace.sessions, restarted),
        active_session_id=restarted.session_id,
    )


_SCORED_FIELDS = (
    "disposition",
    "primary_violation",
    "severity",
    "escalate",
)


def _field_value(judgment: ModerationJudgment, field: str) -> str:
    value = getattr(judgment, field)
    return (
        str(value.value)
        if hasattr(value, "value")
        else ("true" if value else "false")
    )


def _comparison_state(
    judgment: ModerationJudgment,
    reference: ReferenceDecision | None,
) -> tuple[ComparisonState, Mapping[str, ComparisonState]]:
    if reference is None:
        return (
            ComparisonState.NOT_SCORABLE,
            dict.fromkeys(_SCORED_FIELDS, ComparisonState.NOT_SCORABLE),
        )
    if judgment == reference.preferred:
        return (
            ComparisonState.EXACT_MATCH,
            dict.fromkeys(_SCORED_FIELDS, ComparisonState.EXACT_MATCH),
        )
    if judgment in reference.acceptable_alternatives:
        return (
            ComparisonState.ACCEPTABLE_ALTERNATIVE,
            dict.fromkeys(
                _SCORED_FIELDS, ComparisonState.ACCEPTABLE_ALTERNATIVE
            ),
        )
    return (
        ComparisonState.DISAGREEMENT,
        {
            field: (
                ComparisonState.EXACT_MATCH
                if _field_value(judgment, field)
                == _field_value(reference.preferred, field)
                else ComparisonState.DISAGREEMENT
            )
            for field in _SCORED_FIELDS
        },
    )


def _educational_flags(
    case: ModerationTrainingCase,
    decision: TraineeDecision,
    reference: ReferenceDecision | None,
) -> tuple[str, ...]:
    if reference is None:
        return ()
    trainee = decision.judgment
    preferred = reference.preferred
    flags: list[str] = []
    if (
        preferred.severity is ModerationSeverity.CRITICAL
        and preferred.escalate
        and not trainee.escalate
    ):
        flags.append("critical_escalation_miss")
    if (
        preferred.primary_violation is ViolationCategory.NO_VIOLATION
        and preferred.disposition is ModerationDisposition.ALLOW
        and trainee.disposition
        in (ModerationDisposition.WARN, ModerationDisposition.REMOVE)
    ):
        flags.append("over_enforcement")
    if (
        preferred.severity
        in (ModerationSeverity.HIGH, ModerationSeverity.CRITICAL)
        and preferred.disposition is ModerationDisposition.REMOVE
        and trainee.disposition
        in (ModerationDisposition.ALLOW, ModerationDisposition.WARN)
    ):
        flags.append("high_severity_under_enforcement")
    if not preferred.escalate and trainee.escalate:
        flags.append("unnecessary_escalation")
    if (
        preferred.disposition
        is ModerationDisposition.UNCLEAR_NEEDS_REVIEW
        and trainee.disposition
        is not ModerationDisposition.UNCLEAR_NEEDS_REVIEW
        and case.ambiguity_level is AmbiguityLevel.HIGH
    ):
        flags.append("false_certainty_under_insufficient_context")
    if (
        case.learning_objective
        is LearningObjective.SENTIMENT_IS_NOT_HARMFULNESS
        and preferred.primary_violation is ViolationCategory.NO_VIOLATION
        and trainee.primary_violation
        is not ViolationCategory.NO_VIOLATION
    ):
        flags.append("sentiment_confused_with_policy_violation")
    return tuple(flags)


def compare_attempt(
    frozen: FrozenTrainingCase, attempt: CaseAttempt
) -> CaseComparison:
    reference = frozen.frozen_reference
    first_overall, first_states = _comparison_state(
        attempt.first_decision.judgment, reference
    )
    final_overall, final_states = _comparison_state(
        attempt.final_decision.judgment, reference
    )
    fields = tuple(
        FieldComparison(
            field=field,
            first=first_states[field],
            final=final_states[field],
            trainee_first=_field_value(
                attempt.first_decision.judgment, field
            ),
            trainee_final=_field_value(
                attempt.final_decision.judgment, field
            ),
            reference=(
                _field_value(reference.preferred, field)
                if reference is not None
                else ""
            ),
        )
        for field in _SCORED_FIELDS
    )
    flags = tuple(
        dict.fromkeys(
            (
                *_educational_flags(
                    frozen.case, attempt.first_decision, reference
                ),
                *_educational_flags(
                    frozen.case, attempt.final_decision, reference
                ),
            )
        )
    )
    return CaseComparison(
        case_id=frozen.case.case_id,
        fields=fields,
        first_overall=first_overall,
        final_overall=final_overall,
        first_guidance_warnings=tuple(
            item.value for item in attempt.first_decision.guidance_warnings
        ),
        final_guidance_warnings=tuple(
            item.value for item in attempt.final_decision.guidance_warnings
        ),
        educational_flags=flags,
        reference_provenance=(
            reference.provenance if reference is not None else None
        ),
    )


def _metric(
    name: str,
    comparisons: Sequence[CaseComparison],
    *,
    final: bool,
    field: str,
    total_cases: int,
) -> SummaryMetric:
    states = [
        next(item for item in comparison.fields if item.field == field)
        for comparison in comparisons
    ]
    values = [item.final if final else item.first for item in states]
    eligible = [
        value
        for value in values
        if value
        not in (
            ComparisonState.NOT_SCORABLE,
            ComparisonState.MISSING_REQUIRED_FIELD,
        )
    ]
    aligned = sum(
        value
        in (
            ComparisonState.EXACT_MATCH,
            ComparisonState.ACCEPTABLE_ALTERNATIVE,
        )
        for value in eligible
    )
    return SummaryMetric(
        name=name,
        numerator=aligned,
        denominator=len(eligible),
        excluded=total_cases - len(eligible),
        sample=sample_size_assessment(len(eligible)),
    )


def summarize_training_session(
    session: ModerationTrainingSession,
) -> SessionSummary:
    frozen = {item.case.case_id: item for item in session.cases}
    comparisons = tuple(
        compare_attempt(frozen[item.case_id], item)
        for item in session.attempts
    )
    first_metrics = tuple(
        _metric(
            field,
            comparisons,
            final=False,
            field=field,
            total_cases=len(session.cases),
        )
        for field in _SCORED_FIELDS
    )
    final_metrics = tuple(
        _metric(
            field,
            comparisons,
            final=True,
            field=field,
            total_cases=len(session.cases),
        )
        for field in _SCORED_FIELDS
    )
    attempt_by_id = {item.case_id: item for item in session.attempts}
    ai_pairs = [
        (
            attempt_by_id[item.case.case_id].final_decision.judgment,
            item.case.mock_recommendation.judgment,
        )
        for item in session.cases
        if item.case.case_id in attempt_by_id
        and item.case.mock_recommendation is not None
    ]
    ai_reference_pairs = [
        (
            item.case.mock_recommendation.judgment,
            item.frozen_reference,
        )
        for item in session.cases
        if item.case.mock_recommendation is not None
        and item.frozen_reference is not None
    ]
    trainee_ai = SummaryMetric(
        name="trainee_ai_agreement",
        numerator=sum(left == right for left, right in ai_pairs),
        denominator=len(ai_pairs),
        excluded=len(session.cases) - len(ai_pairs),
        sample=sample_size_assessment(len(ai_pairs)),
    )
    ai_reference = SummaryMetric(
        name="ai_reference_alignment",
        numerator=sum(
            ai == reference.preferred
            or ai in reference.acceptable_alternatives
            for ai, reference in ai_reference_pairs
        ),
        denominator=len(ai_reference_pairs),
        excluded=len(session.cases) - len(ai_reference_pairs),
        sample=sample_size_assessment(len(ai_reference_pairs)),
    )
    category_rows: list[CategorySummary] = []
    for category in ViolationCategory:
        eligible: list[CaseComparison] = []
        for comparison in comparisons:
            reference = frozen[comparison.case_id].frozen_reference
            if (
                reference is not None
                and reference.preferred.primary_violation is category
            ):
                eligible.append(comparison)
        if eligible:
            category_rows.append(
                CategorySummary(
                    category=category,
                    exact_or_acceptable=sum(
                        item.final_overall
                        in (
                            ComparisonState.EXACT_MATCH,
                            ComparisonState.ACCEPTABLE_ALTERNATIVE,
                        )
                        for item in eligible
                    ),
                    denominator=len(eligible),
                    sample=sample_size_assessment(len(eligible)),
                )
            )
    severity_rows: list[SeveritySummary] = []
    for severity in ModerationSeverity:
        eligible = []
        for comparison in comparisons:
            reference = frozen[comparison.case_id].frozen_reference
            if (
                reference is not None
                and reference.preferred.severity is severity
            ):
                eligible.append(comparison)
        if eligible:
            severity_rows.append(
                SeveritySummary(
                    severity=severity,
                    exact_or_acceptable=sum(
                        item.final_overall
                        in (
                            ComparisonState.EXACT_MATCH,
                            ComparisonState.ACCEPTABLE_ALTERNATIVE,
                        )
                        for item in eligible
                    ),
                    denominator=len(eligible),
                    sample=sample_size_assessment(len(eligible)),
                )
            )
    provenance = Counter(
        item.frozen_reference.provenance
        for item in session.cases
        if item.frozen_reference is not None
    )
    flags = Counter(
        flag for item in comparisons for flag in item.educational_flags
    )
    reference_eligible = tuple(
        item
        for item in comparisons
        if item.final_overall is not ComparisonState.NOT_SCORABLE
    )
    alternative_count = sum(
        item.final_overall is ComparisonState.ACCEPTABLE_ALTERNATIVE
        for item in reference_eligible
    )
    return SessionSummary(
        session_id=session.session_id,
        total_cases=len(session.cases),
        completed_cases=len(session.attempts),
        unscored_cases=sum(
            item.frozen_reference is None for item in session.cases
        ),
        ai_available_cases=sum(
            item.case.mock_recommendation is not None
            for item in session.cases
        ),
        first_metrics=first_metrics,
        final_metrics=final_metrics,
        acceptable_alternative_count=alternative_count,
        acceptable_alternative_alignment=SummaryMetric(
            name="acceptable_alternative_rate",
            numerator=alternative_count,
            denominator=len(reference_eligible),
            excluded=len(session.cases) - len(reference_eligible),
            sample=sample_size_assessment(len(reference_eligible)),
        ),
        trainee_ai_agreement=trainee_ai,
        ai_reference_alignment=ai_reference,
        categories=tuple(category_rows),
        severities=tuple(severity_rows),
        reference_provenance_counts=tuple(
            (item, provenance[item]) for item in ReferenceProvenance
        ),
        educational_flag_counts=tuple(sorted(flags.items())),
    )


MODERATION_EXPORT_FIELDS = (
    "section",
    "export_type",
    "exported_at",
    "policy_id",
    "policy_version",
    "metric_definitions",
    "insufficient_sample_below",
    "small_sample_below",
    "session_id",
    "session_mode",
    "feedback_timing",
    "case_count",
    "completed_count",
    "scored_count",
    "excluded_count",
    "ai_available_count",
    "first_attempt_semantics",
    "final_decision_semantics",
    "mock_provider_id",
    "mock_provider_version",
    "source_text_included",
    "metric_name",
    "metric_numerator",
    "metric_denominator",
    "metric_excluded",
    "metric_rate",
    "sample_status",
    "sample_warning",
    "case_id",
    "fixture_version",
    "case_source",
    "case_topic",
    "case_context",
    "source_record_id",
    "excerpted",
    "excerpt_provenance",
    "ambiguity_level",
    "categories_involved",
    "difficulty",
    "learning_objective",
    "safety_sensitive",
    "policy_clause_ids",
    "trainee_first_disposition",
    "trainee_first_primary_violation",
    "trainee_first_secondary_violations",
    "trainee_first_severity",
    "trainee_first_escalate",
    "trainee_first_escalation_reason",
    "trainee_first_unclear_reasons",
    "trainee_first_reasoning",
    "trainee_first_reviewer_note",
    "trainee_first_guidance_warnings",
    "trainee_final_disposition",
    "trainee_final_primary_violation",
    "trainee_final_secondary_violations",
    "trainee_final_severity",
    "trainee_final_escalate",
    "trainee_final_escalation_reason",
    "trainee_final_unclear_reasons",
    "trainee_final_reasoning",
    "trainee_final_reviewer_note",
    "trainee_final_guidance_warnings",
    "feedback_viewed",
    "revision_count",
    "preferred_reference",
    "reference_rationale",
    "acceptable_alternatives",
    "reference_provenance",
    "mock_ai_recommendation",
    "mock_ai_rationale",
    "field_comparison_states",
    "educational_flags",
    "first_submitted_at",
    "final_submitted_at",
    "source_text",
    "sentiment_signal",
    "emotion_signal",
    "context_notes",
    "trusted_metadata",
)


def _judgment_cell(judgment: ModerationJudgment) -> str:
    return "|".join(
        (
            judgment.disposition.value,
            judgment.primary_violation.value,
            "+".join(item.value for item in judgment.secondary_violations),
            judgment.severity.value,
            "true" if judgment.escalate else "false",
            judgment.escalation_reason.value
            if judgment.escalation_reason
            else "",
            "+".join(item.value for item in judgment.unclear_reasons),
        )
    )


def _decision_fields(
    prefix: str, decision: TraineeDecision
) -> dict[str, object]:
    judgment = decision.judgment
    return {
        f"{prefix}_disposition": judgment.disposition,
        f"{prefix}_primary_violation": judgment.primary_violation,
        f"{prefix}_secondary_violations": "|".join(
            item.value for item in judgment.secondary_violations
        ),
        f"{prefix}_severity": judgment.severity,
        f"{prefix}_escalate": "true" if judgment.escalate else "false",
        f"{prefix}_escalation_reason": judgment.escalation_reason or "",
        f"{prefix}_unclear_reasons": "|".join(
            item.value for item in judgment.unclear_reasons
        ),
        f"{prefix}_reasoning": safe_spreadsheet_text(decision.reasoning),
        f"{prefix}_reviewer_note": safe_spreadsheet_text(
            decision.reviewer_note
        ),
        f"{prefix}_guidance_warnings": "|".join(
            item.value for item in decision.guidance_warnings
        ),
    }


def export_moderation_session_csv(
    session: ModerationTrainingSession,
    *,
    include_user_source_text: bool,
    include_signals: bool,
    include_context_notes: bool,
    include_trusted_metadata: bool,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> str:
    if not session.attempts:
        raise ValidationError(
            field="export",
            code="no_eligible_results",
            message="Submit at least one decision before exporting results.",
        )
    timestamp = now()
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Export timestamp must be timezone-aware.")
    summary = summarize_training_session(session)
    first_case = session.cases[0]
    providers = [
        item.case.mock_recommendation
        for item in session.cases
        if item.case.mock_recommendation is not None
    ]
    frozen_by_id = {item.case.case_id: item for item in session.cases}
    scored_completed = sum(
        frozen_by_id[item.case_id].frozen_reference is not None
        for item in session.attempts
    )
    metadata: dict[str, object] = {
        "export_type": "moderation_training_results",
        "exported_at": timestamp.astimezone(UTC).isoformat(),
        "policy_id": first_case.frozen_policy_id,
        "policy_version": first_case.frozen_policy_version,
        "metric_definitions": (
            "Reference alignment counts exact preferred or complete acceptable "
            "alternative matches; trainee-AI agreement is not accuracy."
        ),
        "insufficient_sample_below": INSUFFICIENT_SAMPLE_BELOW,
        "small_sample_below": SMALL_SAMPLE_BELOW,
        "session_id": session.session_id,
        "session_mode": session.mode,
        "feedback_timing": session.feedback_timing,
        "case_count": summary.total_cases,
        "completed_count": summary.completed_cases,
        "scored_count": scored_completed,
        "excluded_count": summary.total_cases - scored_completed,
        "ai_available_count": summary.ai_available_cases,
        "first_attempt_semantics": (
            "Immutable first submitted structured moderation training decision."
        ),
        "final_decision_semantics": (
            "Latest explicit revision; never overwrites first attempt."
        ),
        "mock_provider_id": providers[0].provider_id if providers else "",
        "mock_provider_version": (
            providers[0].provider_version if providers else ""
        ),
        "source_text_included": (
            "built_in_default;user_opt_in"
            if include_user_source_text
            else "built_in_default;user_excluded"
        ),
    }
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=MODERATION_EXPORT_FIELDS, lineterminator="\n"
    )
    writer.writeheader()
    writer.writerow({"section": "export_metadata", **metadata})
    summary_metrics = (
        *(
            (f"first_{item.name}", item)
            for item in summary.first_metrics
        ),
        *(
            (f"final_{item.name}", item)
            for item in summary.final_metrics
        ),
        ("trainee_ai_agreement", summary.trainee_ai_agreement),
        ("ai_reference_alignment", summary.ai_reference_alignment),
        (
            "acceptable_alternative_rate",
            summary.acceptable_alternative_alignment,
        ),
    )
    for metric_name, metric in summary_metrics:
        writer.writerow(
            {
                "section": "summary_metric",
                **metadata,
                "metric_name": metric_name,
                "metric_numerator": metric.numerator,
                "metric_denominator": metric.denominator,
                "metric_excluded": metric.excluded,
                "metric_rate": metric.rate,
                "sample_status": metric.sample.level,
                "sample_warning": metric.sample.message or "",
            }
        )
    for category in summary.categories:
        writer.writerow(
            {
                "section": "category_metric",
                **metadata,
                "metric_name": (
                    f"final_primary_category_{category.category.value}"
                ),
                "metric_numerator": category.exact_or_acceptable,
                "metric_denominator": category.denominator,
                "metric_excluded": (
                    summary.total_cases - category.denominator
                ),
                "metric_rate": (
                    category.exact_or_acceptable / category.denominator
                    if category.denominator
                    else 0.0
                ),
                "sample_status": category.sample.level,
                "sample_warning": category.sample.message or "",
            }
        )
    for severity in summary.severities:
        writer.writerow(
            {
                "section": "severity_metric",
                **metadata,
                "metric_name": (
                    f"final_reference_severity_{severity.severity.value}"
                ),
                "metric_numerator": severity.exact_or_acceptable,
                "metric_denominator": severity.denominator,
                "metric_excluded": (
                    summary.total_cases - severity.denominator
                ),
                "metric_rate": (
                    severity.exact_or_acceptable / severity.denominator
                    if severity.denominator
                    else 0.0
                ),
                "sample_status": severity.sample.level,
                "sample_warning": severity.sample.message or "",
            }
        )
    for attempt in session.attempts:
        frozen = frozen_by_id[attempt.case_id]
        case = frozen.case
        comparison = compare_attempt(frozen, attempt)
        reference = frozen.frozen_reference
        snapshot = case.source_snapshot
        include_text = (
            case.source is ModerationCaseSource.BUILT_IN_SYNTHETIC
            or include_user_source_text
        )
        row: dict[str, object] = {
            "section": "case_result",
            **metadata,
            "case_id": safe_spreadsheet_text(case.case_id),
            "fixture_version": safe_spreadsheet_text(
                case.fixture_version
            ),
            "case_source": case.source,
            "case_topic": safe_spreadsheet_text(case.topic),
            "case_context": safe_spreadsheet_text(case.context),
            "source_record_id": (
                safe_spreadsheet_text(snapshot.source_record_id)
                if snapshot
                else ""
            ),
            "excerpted": (
                "true" if snapshot and snapshot.excerpted else "false"
            ),
            "excerpt_provenance": (
                safe_spreadsheet_text(snapshot.excerpt_provenance)
                if snapshot
                else ""
            ),
            "ambiguity_level": case.ambiguity_level,
            "categories_involved": "|".join(
                item.value for item in case.categories_involved
            ),
            "difficulty": case.difficulty,
            "learning_objective": case.learning_objective,
            "safety_sensitive": (
                "true" if case.safety_sensitive else "false"
            ),
            "policy_clause_ids": "|".join(frozen.frozen_clause_ids),
            **_decision_fields(
                "trainee_first", attempt.first_decision
            ),
            **_decision_fields(
                "trainee_final", attempt.final_decision
            ),
            "feedback_viewed": (
                "true" if attempt.feedback_viewed else "false"
            ),
            "revision_count": attempt.revision_count,
            "preferred_reference": (
                _judgment_cell(reference.preferred) if reference else ""
            ),
            "reference_rationale": (
                safe_spreadsheet_text(reference.rationale)
                if reference
                else ""
            ),
            "acceptable_alternatives": (
                "||".join(
                    _judgment_cell(item)
                    for item in reference.acceptable_alternatives
                )
                if reference
                else ""
            ),
            "reference_provenance": (
                reference.provenance if reference else ""
            ),
            "mock_ai_recommendation": (
                _judgment_cell(case.mock_recommendation.judgment)
                if case.mock_recommendation
                else ""
            ),
            "mock_ai_rationale": (
                safe_spreadsheet_text(
                    case.mock_recommendation.rationale
                )
                if case.mock_recommendation
                else ""
            ),
            "field_comparison_states": "|".join(
                f"{item.field}:{item.first.value}->{item.final.value}"
                for item in comparison.fields
            ),
            "educational_flags": "|".join(
                comparison.educational_flags
            ),
            "first_submitted_at": (
                attempt.first_submitted_at.astimezone(UTC).isoformat()
            ),
            "final_submitted_at": (
                attempt.final_submitted_at.astimezone(UTC).isoformat()
            ),
            "source_text": (
                safe_spreadsheet_text(case.text) if include_text else ""
            ),
        }
        if snapshot is not None and include_signals:
            row["sentiment_signal"] = (
                safe_spreadsheet_text(
                    "|".join(
                        (
                            snapshot.sentiment.label,
                            str(snapshot.sentiment.confidence),
                            snapshot.sentiment.model_name,
                            snapshot.sentiment.revision,
                        )
                    )
                )
                if snapshot.sentiment
                else ""
            )
            row["emotion_signal"] = (
                safe_spreadsheet_text(
                    "|".join(
                        (
                            snapshot.emotion.dominant_emotion,
                            "+".join(
                                snapshot.emotion.secondary_emotions
                            ),
                            str(snapshot.emotion.confidence),
                            str(snapshot.emotion.threshold),
                            snapshot.emotion.model_name,
                            snapshot.emotion.revision,
                        )
                    )
                )
                if snapshot.emotion
                else ""
            )
        if snapshot is not None and include_context_notes:
            row["context_notes"] = safe_spreadsheet_text(
                "||".join(
                    "|".join(
                        (
                            note.association,
                            note.association_value,
                            note.phrase,
                            note.explanation,
                            note.context_importance,
                            "+".join(note.tags),
                            note.created_at.astimezone(UTC).isoformat(),
                        )
                    )
                    for note in snapshot.context_notes
                )
            )
        if snapshot is not None and include_trusted_metadata:
            row["trusted_metadata"] = safe_spreadsheet_text(
                "|".join(
                    f"{key}={value}"
                    for key, value in snapshot.trusted_metadata
                )
            )
        writer.writerow(row)
    return output.getvalue()
