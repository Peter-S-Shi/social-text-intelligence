"""Typed contracts for the local synthetic moderation training workflow."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .errors import ValidationError

MAX_REASONING_LENGTH = 2_000
MAX_REVIEWER_NOTE_LENGTH = 2_000
MAX_RATIONALE_LENGTH = 3_000
MAX_CASE_TEXT_LENGTH = 20_000
MAX_CONTEXT_LENGTH = 4_000


class ModerationDisposition(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    REMOVE = "remove"
    UNCLEAR_NEEDS_REVIEW = "unclear_needs_review"


class ViolationCategory(StrEnum):
    NO_VIOLATION = "no_violation"
    HARASSMENT_ABUSE = "harassment_abuse"
    HATE_PROTECTED_CLASS_ATTACK = "hate_protected_class_attack"
    THREAT_VIOLENCE = "threat_violence"
    SELF_HARM = "self_harm"
    SEXUAL_EXPLICIT_CONTENT = "sexual_explicit_content"
    SPAM_MANIPULATION = "spam_manipulation"
    PRIVACY_PERSONAL_INFORMATION = "privacy_personal_information"
    ILLEGAL_DANGEROUS_ACTIVITY = "illegal_dangerous_activity"


class ModerationSeverity(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationReason(StrEnum):
    IMMINENT_SAFETY_RISK = "imminent_safety_risk"
    CREDIBLE_THREAT = "credible_threat"
    SELF_HARM_RISK = "self_harm_risk"
    CHILD_SAFETY_CONCERN = "child_safety_concern"
    LEGAL_OR_REGULATORY_CONCERN = "legal_or_regulatory_concern"
    PRIVACY_OR_DOXXING_CONCERN = "privacy_or_doxxing_concern"
    POLICY_AMBIGUITY = "policy_ambiguity"
    SPECIALIST_OR_SENIOR_REVIEW = "specialist_or_senior_review"
    OTHER = "other"


class UnclearReason(StrEnum):
    INSUFFICIENT_CONTEXT = "insufficient_context"
    AMBIGUOUS_LANGUAGE = "ambiguous_language"
    CONFLICTING_POLICY_SIGNALS = "conflicting_policy_signals"
    SPECIALIST_KNOWLEDGE_REQUIRED = "specialist_knowledge_required"
    POSSIBLE_IMMINENT_RISK_REVIEW = "possible_imminent_risk_review"
    OTHER = "other"


class GuidanceWarning(StrEnum):
    ALLOW_WITH_VIOLATION = "allow_with_violation"
    CRITICAL_WITHOUT_ESCALATION = "critical_without_escalation"
    HIGH_SEVERITY_LIGHT_DISPOSITION = "high_severity_light_disposition"
    NO_VIOLATION_WITH_NON_NONE_SEVERITY = (
        "no_violation_with_non_none_severity"
    )
    NONE_SEVERITY_WITH_VIOLATION = "none_severity_with_violation"
    LOW_SEVERITY_REMOVE = "low_severity_remove"
    MEDIUM_SEVERITY_ALLOW = "medium_severity_allow"


class ReferenceProvenance(StrEnum):
    BUILT_IN = "built_in"
    SELF_AUTHORED = "self_authored"
    USER_AUTHORED = "user_authored"


class ModerationCaseSource(StrEnum):
    BUILT_IN_SYNTHETIC = "built_in_synthetic"
    WORKSPACE_RECORD = "workspace_record"


class PolicySourceType(StrEnum):
    BUILT_IN_SYNTHETIC_POLICY = "built_in_synthetic_policy"


class CaseDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class AmbiguityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LearningObjective(StrEnum):
    HARASSMENT_VS_HATE = "harassment_vs_hate"
    SENTIMENT_IS_NOT_HARMFULNESS = "sentiment_is_not_harmfulness"
    ESCALATION_WITHOUT_AUTOMATIC_REMOVAL = (
        "escalation_without_automatic_removal"
    )
    INSUFFICIENT_CONTEXT = "insufficient_context"
    AI_UNDER_ENFORCEMENT = "ai_under_enforcement"
    AI_OVER_ENFORCEMENT = "ai_over_enforcement"
    SEVERITY_VS_DISPOSITION = "severity_vs_disposition"
    POLICY_VS_FACTUAL_UNCERTAINTY = "policy_vs_factual_uncertainty"


class TrainingMode(StrEnum):
    INDEPENDENT = "independent"
    AI_ASSISTED = "ai_assisted"


class FeedbackTiming(StrEnum):
    IMMEDIATE = "immediate_feedback"
    END_OF_SESSION = "end_of_session_review"


class CaseOrderMode(StrEnum):
    RANDOM = "random"
    DIFFICULTY_PROGRESSION = "difficulty_progression"
    ORIGINAL_ORDER = "original_order"


class TrainingSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ComparisonState(StrEnum):
    EXACT_MATCH = "exact_match"
    ACCEPTABLE_ALTERNATIVE = "acceptable_alternative"
    DISAGREEMENT = "disagreement"
    NOT_SCORABLE = "not_scorable"
    MISSING_REQUIRED_FIELD = "missing_required_field"


def _clean_required(value: str, *, field: str, limit: int) -> str:
    cleaned = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    ).strip()
    if not cleaned:
        raise ValidationError(
            field=field,
            code="required",
            message=f"{field} is required.",
        )
    if len(cleaned) > limit:
        raise ValidationError(
            field=field,
            code="too_long",
            message=f"{field} exceeds {limit} characters.",
        )
    return cleaned


def _require_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(
            field=field,
            code="timezone_required",
            message=f"{field} must be timezone-aware.",
        )
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ModerationJudgment:
    disposition: ModerationDisposition
    primary_violation: ViolationCategory
    secondary_violations: tuple[ViolationCategory, ...]
    severity: ModerationSeverity
    escalate: bool
    escalation_reason: EscalationReason | None = None
    unclear_reasons: tuple[UnclearReason, ...] = ()

    def __post_init__(self) -> None:
        if len(self.secondary_violations) != len(set(self.secondary_violations)):
            raise ValidationError(
                field="secondary_violations",
                code="duplicate_violation",
                message="Secondary violations must be unique.",
            )
        if self.primary_violation in self.secondary_violations:
            raise ValidationError(
                field="secondary_violations",
                code="primary_repeated",
                message="The primary violation cannot also be secondary.",
            )
        selected = {self.primary_violation, *self.secondary_violations}
        if (
            ViolationCategory.NO_VIOLATION in selected
            and len(selected) > 1
        ):
            raise ValidationError(
                field="primary_violation",
                code="no_violation_conflict",
                message="No violation cannot coexist with violation categories.",
            )
        if (
            self.disposition
            in (ModerationDisposition.WARN, ModerationDisposition.REMOVE)
            and self.primary_violation is ViolationCategory.NO_VIOLATION
        ):
            raise ValidationError(
                field="primary_violation",
                code="violation_required",
                message="Warn and Remove require a primary violation category.",
            )
        if self.escalate and self.escalation_reason is None:
            raise ValidationError(
                field="escalation_reason",
                code="escalation_reason_required",
                message="Select an escalation reason when escalation is required.",
            )
        if not self.escalate and self.escalation_reason is not None:
            raise ValidationError(
                field="escalation_reason",
                code="unexpected_escalation_reason",
                message="An escalation reason requires escalation.",
            )
        if (
            self.disposition is ModerationDisposition.UNCLEAR_NEEDS_REVIEW
            and not self.unclear_reasons
        ):
            raise ValidationError(
                field="unclear_reasons",
                code="unclear_reason_required",
                message="Unclear / Needs Review requires at least one reason.",
            )
        if (
            self.disposition is not ModerationDisposition.UNCLEAR_NEEDS_REVIEW
            and self.unclear_reasons
        ):
            raise ValidationError(
                field="unclear_reasons",
                code="unexpected_unclear_reason",
                message="Unclear reasons require Unclear / Needs Review.",
            )
        if len(self.unclear_reasons) != len(set(self.unclear_reasons)):
            raise ValidationError(
                field="unclear_reasons",
                code="duplicate_unclear_reason",
                message="Unclear reasons must be unique.",
            )


def guidance_warnings(
    judgment: ModerationJudgment,
) -> tuple[GuidanceWarning, ...]:
    """Return non-blocking departures from ordinary synthetic-policy guidance."""

    warnings: list[GuidanceWarning] = []
    has_violation = (
        judgment.primary_violation is not ViolationCategory.NO_VIOLATION
    )
    if judgment.disposition is ModerationDisposition.ALLOW and has_violation:
        warnings.append(GuidanceWarning.ALLOW_WITH_VIOLATION)
    if (
        judgment.severity is ModerationSeverity.CRITICAL
        and not judgment.escalate
    ):
        warnings.append(GuidanceWarning.CRITICAL_WITHOUT_ESCALATION)
    if (
        judgment.severity
        in (ModerationSeverity.HIGH, ModerationSeverity.CRITICAL)
        and judgment.disposition
        in (ModerationDisposition.ALLOW, ModerationDisposition.WARN)
    ):
        warnings.append(GuidanceWarning.HIGH_SEVERITY_LIGHT_DISPOSITION)
    if (
        not has_violation
        and judgment.severity is not ModerationSeverity.NONE
    ):
        warnings.append(
            GuidanceWarning.NO_VIOLATION_WITH_NON_NONE_SEVERITY
        )
    if has_violation and judgment.severity is ModerationSeverity.NONE:
        warnings.append(GuidanceWarning.NONE_SEVERITY_WITH_VIOLATION)
    if (
        judgment.severity is ModerationSeverity.LOW
        and judgment.disposition is ModerationDisposition.REMOVE
    ):
        warnings.append(GuidanceWarning.LOW_SEVERITY_REMOVE)
    if (
        judgment.severity is ModerationSeverity.MEDIUM
        and judgment.disposition is ModerationDisposition.ALLOW
    ):
        warnings.append(GuidanceWarning.MEDIUM_SEVERITY_ALLOW)
    return tuple(warnings)


@dataclass(frozen=True, slots=True)
class TraineeDecision:
    judgment: ModerationJudgment
    reasoning: str
    reviewer_note: str
    guidance_warnings: tuple[GuidanceWarning, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reasoning",
            _clean_required(
                self.reasoning,
                field="reasoning",
                limit=MAX_REASONING_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "reviewer_note",
            _clean_required(
                self.reviewer_note,
                field="reviewer_note",
                limit=MAX_REVIEWER_NOTE_LENGTH,
            ),
        )
        expected = guidance_warnings(self.judgment)
        if self.guidance_warnings != expected:
            raise ValidationError(
                field="guidance_warnings",
                code="warning_mismatch",
                message="Guidance warnings must match the submitted decision.",
            )

    @classmethod
    def create(
        cls,
        judgment: ModerationJudgment,
        *,
        reasoning: str,
        reviewer_note: str,
    ) -> TraineeDecision:
        return cls(
            judgment=judgment,
            reasoning=reasoning,
            reviewer_note=reviewer_note,
            guidance_warnings=guidance_warnings(judgment),
        )


@dataclass(frozen=True, slots=True)
class ReferenceDecision:
    preferred: ModerationJudgment
    acceptable_alternatives: tuple[ModerationJudgment, ...]
    rationale: str
    policy_clause_ids: tuple[str, ...]
    provenance: ReferenceProvenance

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rationale",
            _clean_required(
                self.rationale,
                field="reference_rationale",
                limit=MAX_RATIONALE_LENGTH,
            ),
        )
        if not self.policy_clause_ids:
            raise ValidationError(
                field="policy_clause_ids",
                code="required",
                message="A reference decision requires policy clauses.",
            )
        if len(self.policy_clause_ids) != len(set(self.policy_clause_ids)):
            raise ValidationError(
                field="policy_clause_ids",
                code="duplicate_clause",
                message="Referenced policy clauses must be unique.",
            )
        all_decisions = (self.preferred, *self.acceptable_alternatives)
        if len(all_decisions) != len(set(all_decisions)):
            raise ValidationError(
                field="acceptable_alternatives",
                code="duplicate_alternative",
                message="Acceptable alternatives must be distinct complete decisions.",
            )


@dataclass(frozen=True, slots=True)
class MockModerationRecommendation:
    judgment: ModerationJudgment
    rationale: str
    provider_id: str
    provider_version: str
    provenance: str = "synthetic_mock"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rationale",
            _clean_required(
                self.rationale,
                field="mock_rationale",
                limit=MAX_RATIONALE_LENGTH,
            ),
        )
        for field, value in (
            ("provider_id", self.provider_id),
            ("provider_version", self.provider_version),
        ):
            object.__setattr__(
                self,
                field,
                _clean_required(value, field=field, limit=128),
            )
        if self.provenance != "synthetic_mock":
            raise ValidationError(
                field="provenance",
                code="invalid_mock_provenance",
                message="Mock recommendations require synthetic_mock provenance.",
            )


@dataclass(frozen=True, slots=True)
class PolicyClause:
    clause_id: str
    text: str


@dataclass(frozen=True, slots=True)
class PolicyCategory:
    category_id: ViolationCategory
    display_name: str
    definition: str
    included_examples: tuple[str, ...]
    excluded_examples: tuple[str, ...]
    severity_guidance: str
    disposition_guidance: str
    escalation_triggers: tuple[str, ...]
    clauses: tuple[PolicyClause, ...]


@dataclass(frozen=True, slots=True)
class ModerationPolicy:
    policy_id: str
    policy_version: str
    name: str
    source_type: PolicySourceType
    categories: tuple[PolicyCategory, ...]


@dataclass(frozen=True, slots=True)
class SentimentSignalSnapshot:
    label: str
    confidence: float
    model_name: str
    revision: str


@dataclass(frozen=True, slots=True)
class EmotionSignalSnapshot:
    dominant_emotion: str
    secondary_emotions: tuple[str, ...]
    confidence: float
    threshold: float
    model_name: str
    revision: str


@dataclass(frozen=True, slots=True)
class HumanReviewSnapshot:
    status: str
    sentiment_judgment: str
    human_sentiment: str
    emotion_judgment: str
    human_dominant_emotion: str
    human_secondary_emotions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextNoteSnapshot:
    association: str
    association_value: str
    phrase: str
    explanation: str
    context_importance: str
    tags: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "created_at",
            _require_utc(self.created_at, field="context_note_created_at"),
        )


@dataclass(frozen=True, slots=True)
class SourceRecordSnapshot:
    source_record_id: str
    text: str
    excerpted: bool
    excerpt_provenance: str
    trusted_metadata: tuple[tuple[str, str], ...]
    sentiment: SentimentSignalSnapshot | None
    emotion: EmotionSignalSnapshot | None
    human_review: HumanReviewSnapshot | None
    context_notes: tuple[ContextNoteSnapshot, ...]


@dataclass(frozen=True, slots=True)
class ModerationTrainingCase:
    case_id: str
    fixture_version: str
    source: ModerationCaseSource
    policy_id: str
    policy_version: str
    difficulty: CaseDifficulty
    topic: str
    categories_involved: tuple[ViolationCategory, ...]
    context_available: bool
    ambiguity_level: AmbiguityLevel
    safety_sensitive: bool
    learning_objective: LearningObjective
    text: str
    context: str
    reference: ReferenceDecision | None
    mock_recommendation: MockModerationRecommendation | None
    source_snapshot: SourceRecordSnapshot | None = None
    original_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            _clean_required(
                self.text, field="case_text", limit=MAX_CASE_TEXT_LENGTH
            ),
        )
        if len(self.context) > MAX_CONTEXT_LENGTH:
            raise ValidationError(
                field="case_context",
                code="too_long",
                message=f"case_context exceeds {MAX_CONTEXT_LENGTH} characters.",
            )
        if self.source is ModerationCaseSource.BUILT_IN_SYNTHETIC:
            if self.source_snapshot is not None:
                raise ValidationError(
                    field="source_snapshot",
                    code="unexpected_snapshot",
                    message="Built-in cases cannot contain user workspace snapshots.",
                )
            if (
                self.reference is None
                or self.reference.provenance is not ReferenceProvenance.BUILT_IN
            ):
                raise ValidationError(
                    field="reference",
                    code="invalid_builtin_reference",
                    message="Built-in cases require built-in reference provenance.",
                )
        elif self.source_snapshot is None:
            raise ValidationError(
                field="source_snapshot",
                code="missing_snapshot",
                message="Workspace-derived cases require a frozen source snapshot.",
            )


@dataclass(frozen=True, slots=True)
class FrozenTrainingCase:
    case: ModerationTrainingCase
    frozen_reference: ReferenceDecision | None
    frozen_policy_id: str
    frozen_policy_version: str
    frozen_clause_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaseAttempt:
    case_id: str
    first_decision: TraineeDecision
    final_decision: TraineeDecision
    first_submitted_at: datetime
    final_submitted_at: datetime
    feedback_viewed: bool = False
    revision_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "first_submitted_at",
            _require_utc(
                self.first_submitted_at, field="first_submitted_at"
            ),
        )
        object.__setattr__(
            self,
            "final_submitted_at",
            _require_utc(
                self.final_submitted_at, field="final_submitted_at"
            ),
        )
        if self.revision_count < 0:
            raise ValidationError(
                field="revision_count",
                code="invalid_revision_count",
                message="Revision count cannot be negative.",
            )


@dataclass(frozen=True, slots=True)
class ModerationTrainingSession:
    session_id: str
    cases: tuple[FrozenTrainingCase, ...]
    mode: TrainingMode
    feedback_timing: FeedbackTiming
    order_mode: CaseOrderMode
    attempts: tuple[CaseAttempt, ...]
    status: TrainingSessionStatus
    created_at: datetime
    imbalance_note: str = ""
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "created_at", _require_utc(self.created_at, field="created_at")
        )
        if self.cancelled_at is not None:
            object.__setattr__(
                self,
                "cancelled_at",
                _require_utc(self.cancelled_at, field="cancelled_at"),
            )
        if self.completed_at is not None:
            object.__setattr__(
                self,
                "completed_at",
                _require_utc(self.completed_at, field="completed_at"),
            )
        case_ids = tuple(item.case.case_id for item in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValidationError(
                field="cases",
                code="duplicate_case",
                message="A session cannot contain duplicate cases.",
            )
        attempt_ids = tuple(item.case_id for item in self.attempts)
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValidationError(
                field="attempts",
                code="duplicate_submission",
                message="A case can have only one attempt per session.",
            )
