"""Typed contracts for the local support triage workbench."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .errors import ValidationError

MAX_NOTE_LENGTH = 2_000
MAX_TEXT_LENGTH = 20_000
MAX_EXCERPT_LENGTH = 4_000
MAX_LABEL_LENGTH = 200


class SupportIntent(StrEnum):
    REQUEST_INFORMATION = "request_information"
    REQUEST_STATUS_UPDATE = "request_status_update"
    REPORT_TECHNICAL_PROBLEM = "report_technical_problem"
    REPORT_PRODUCT_OR_SERVICE_PROBLEM = "report_product_or_service_problem"
    REQUEST_REFUND = "request_refund"
    REQUEST_CANCELLATION = "request_cancellation"
    DISPUTE_CHARGE_OR_PAYMENT = "dispute_charge_or_payment"
    RECOVER_ACCOUNT_ACCESS = "recover_account_access"
    CHANGE_ACCOUNT_DETAILS = "change_account_details"
    REPORT_FRAUD_OR_SECURITY_CONCERN = "report_fraud_or_security_concern"
    REPORT_SAFETY_OR_ABUSE_CONCERN = "report_safety_or_abuse_concern"
    SUBMIT_COMPLAINT = "submit_complaint"
    PROVIDE_FEEDBACK = "provide_feedback"
    REQUEST_FEATURE = "request_feature"
    OTHER_OR_UNCLEAR = "other_or_unclear"


class IssueCategory(StrEnum):
    ACCOUNT_AND_ACCESS = "account_and_access"
    BILLING_AND_PAYMENT = "billing_and_payment"
    REFUND_AND_CANCELLATION = "refund_and_cancellation"
    TECHNICAL_PROBLEM = "technical_problem"
    PRODUCT_OR_SERVICE_ISSUE = "product_or_service_issue"
    ORDER_DELIVERY_OR_STATUS = "order_delivery_or_status"
    POLICY_OR_ELIGIBILITY_QUESTION = "policy_or_eligibility_question"
    SAFETY_OR_ABUSE_CONCERN = "safety_or_abuse_concern"
    FRAUD_OR_SECURITY_CONCERN = "fraud_or_security_concern"
    FEEDBACK_OR_FEATURE_REQUEST = "feedback_or_feature_request"
    OTHER_OR_UNCLEAR = "other_or_unclear"


class TriageUrgency(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    UNCLEAR = "unclear"


class RecommendedQueue(StrEnum):
    GENERAL_SUPPORT = "general_support"
    ACCOUNT_AND_ACCESS = "account_and_access"
    BILLING_OPERATIONS = "billing_operations"
    REFUNDS_AND_CANCELLATIONS = "refunds_and_cancellations"
    TECHNICAL_SUPPORT = "technical_support"
    ORDER_AND_DELIVERY_SUPPORT = "order_and_delivery_support"
    TRUST_AND_SAFETY = "trust_and_safety"
    FRAUD_AND_RISK_REVIEW = "fraud_and_risk_review"
    PRODUCT_FEEDBACK = "product_feedback"
    SPECIALIST_OR_MANUAL_REVIEW = "specialist_or_manual_review"


class TriageEscalationReason(StrEnum):
    ACCOUNT_SECURITY_CONCERN = "account_security_concern"
    SUSPECTED_FRAUD = "suspected_fraud"
    SAFETY_OR_ABUSE_CONCERN = "safety_or_abuse_concern"
    LEGAL_OR_REGULATORY_CONCERN = "legal_or_regulatory_concern"
    HIGH_VALUE_BILLING_IMPACT = "high_value_billing_impact"
    REPEATED_UNRESOLVED_ISSUE = "repeated_unresolved_issue"
    SERVICE_WIDE_OR_MULTI_USER_IMPACT = "service_wide_or_multi_user_impact"
    POLICY_AMBIGUITY = "policy_ambiguity"
    SPECIALIST_REVIEW_REQUIRED = "specialist_review_required"
    OTHER = "other"


class NextAction(StrEnum):
    REQUEST_MORE_INFORMATION = "request_more_information"
    VERIFY_IDENTITY_OR_ACCOUNT_OWNERSHIP = (
        "verify_identity_or_account_ownership"
    )
    COLLECT_LOGS_OR_TECHNICAL_DETAILS = "collect_logs_or_technical_details"
    REVIEW_TRANSACTION_OR_BILLING_RECORD = (
        "review_transaction_or_billing_record"
    )
    PROVIDE_POLICY_OR_ELIGIBILITY_INFORMATION = (
        "provide_policy_or_eligibility_information"
    )
    PROCESS_CANCELLATION_OR_REFUND_REVIEW = (
        "process_cancellation_or_refund_review"
    )
    ESCALATE_TO_SPECIALIST = "escalate_to_specialist"
    MONITOR_OR_FOLLOW_UP = "monitor_or_follow_up"
    NO_IMMEDIATE_ACTION = "no_immediate_action"
    OTHER = "other"


class TriageGuidanceWarning(StrEnum):
    CRITICAL_WITHOUT_ESCALATION = "critical_without_escalation"
    SAFETY_TO_GENERAL = "safety_or_abuse_routed_to_general_support"
    FRAUD_TO_GENERAL = "fraud_or_security_routed_to_general_support"
    ACCOUNT_SECURITY_TO_FEEDBACK = "account_security_routed_to_product_feedback"
    ESCALATION_WITH_NO_ACTION = "escalation_with_no_immediate_action"
    LOW_WITH_SERIOUS_ESCALATION = "low_urgency_with_serious_escalation"
    UNCLEAR_TO_SPECIALIST = "unclear_routed_to_specialized_queue"
    REFUND_QUEUE_DEPARTURE = "refund_routed_outside_refund_or_billing"
    TECHNICAL_TO_FEEDBACK = "technical_problem_routed_to_product_feedback"


class TicketSource(StrEnum):
    BUILT_IN_SYNTHETIC = "built_in_synthetic"
    WORKSPACE_RECORD = "workspace_record"


class TicketComplexity(StrEnum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    COMPLEX = "complex"


class MockProvenance(StrEnum):
    BUILT_IN_MOCK = "built_in_mock"
    SELF_AUTHORED_MOCK = "self_authored_mock"
    UNAVAILABLE = "unavailable"


class TriageMode(StrEnum):
    INDEPENDENT = "independent"
    MOCK_ASSISTED = "mock_assisted"


class TicketStatus(StrEnum):
    UNTRIAGED = "untriaged"
    DRAFT = "draft"
    FINALIZED = "finalized"


class FieldComparisonState(StrEnum):
    AGREE = "agree"
    OVERRIDE = "override"
    UNAVAILABLE = "unavailable"


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(
            field=field,
            code="timezone_required",
            message=f"{field} must use timezone-aware UTC.",
        )
    return value.astimezone(UTC)


def clean_text(value: str, *, field: str, limit: int, required: bool) -> str:
    normalized = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    ).strip()
    if required and not normalized:
        raise ValidationError(
            field=field, code="required", message=f"{field} is required."
        )
    if len(normalized) > limit:
        raise ValidationError(
            field=field,
            code="too_long",
            message=f"{field} exceeds {limit} characters.",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class TriageFields:
    primary_intent: SupportIntent | None = None
    secondary_intents: tuple[SupportIntent, ...] = ()
    issue_category: IssueCategory | None = None
    urgency: TriageUrgency | None = None
    recommended_queue: RecommendedQueue | None = None
    escalation_required: bool = False
    escalation_reason: TriageEscalationReason | None = None
    primary_next_action: NextAction | None = None
    secondary_next_actions: tuple[NextAction, ...] = ()
    unclear_reason: str = ""
    human_notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "unclear_reason",
            clean_text(
                self.unclear_reason,
                field="unclear_reason",
                limit=MAX_NOTE_LENGTH,
                required=False,
            ),
        )
        object.__setattr__(
            self,
            "human_notes",
            clean_text(
                self.human_notes,
                field="human_notes",
                limit=MAX_NOTE_LENGTH,
                required=False,
            ),
        )
        if len(self.secondary_intents) > 2:
            raise ValidationError(
                field="secondary_intents",
                code="too_many",
                message="Select at most two secondary intents.",
            )
        if len(self.secondary_intents) != len(set(self.secondary_intents)):
            raise ValidationError(
                field="secondary_intents",
                code="duplicate",
                message="Secondary intents must be unique.",
            )
        if self.primary_intent in self.secondary_intents:
            raise ValidationError(
                field="secondary_intents",
                code="primary_repeated",
                message="Primary intent cannot also be secondary.",
            )
        if len(self.secondary_next_actions) > 2:
            raise ValidationError(
                field="secondary_next_actions",
                code="too_many",
                message="Select at most two secondary next actions.",
            )
        if len(self.secondary_next_actions) != len(
            set(self.secondary_next_actions)
        ):
            raise ValidationError(
                field="secondary_next_actions",
                code="duplicate",
                message="Secondary next actions must be unique.",
            )
        if self.primary_next_action in self.secondary_next_actions:
            raise ValidationError(
                field="secondary_next_actions",
                code="primary_repeated",
                message="Primary next action cannot also be secondary.",
            )
        if self.escalation_required and self.escalation_reason is None:
            raise ValidationError(
                field="escalation_reason",
                code="required",
                message="Escalation requires one supported reason.",
            )
        if not self.escalation_required and self.escalation_reason is not None:
            raise ValidationError(
                field="escalation_reason",
                code="unexpected",
                message="Escalation reason requires escalation.",
            )


def triage_guidance_warnings(
    fields: TriageFields,
) -> tuple[TriageGuidanceWarning, ...]:
    warnings: list[TriageGuidanceWarning] = []
    if (
        fields.urgency is TriageUrgency.CRITICAL
        and not fields.escalation_required
    ):
        warnings.append(TriageGuidanceWarning.CRITICAL_WITHOUT_ESCALATION)
    if (
        fields.issue_category is IssueCategory.SAFETY_OR_ABUSE_CONCERN
        and fields.recommended_queue is RecommendedQueue.GENERAL_SUPPORT
    ):
        warnings.append(TriageGuidanceWarning.SAFETY_TO_GENERAL)
    if (
        fields.issue_category is IssueCategory.FRAUD_OR_SECURITY_CONCERN
        and fields.recommended_queue is RecommendedQueue.GENERAL_SUPPORT
    ):
        warnings.append(TriageGuidanceWarning.FRAUD_TO_GENERAL)
    if (
        fields.escalation_reason
        is TriageEscalationReason.ACCOUNT_SECURITY_CONCERN
        and fields.recommended_queue is RecommendedQueue.PRODUCT_FEEDBACK
    ):
        warnings.append(TriageGuidanceWarning.ACCOUNT_SECURITY_TO_FEEDBACK)
    if (
        fields.escalation_required
        and fields.primary_next_action is NextAction.NO_IMMEDIATE_ACTION
    ):
        warnings.append(TriageGuidanceWarning.ESCALATION_WITH_NO_ACTION)
    if (
        fields.urgency is TriageUrgency.LOW
        and fields.escalation_reason
        in {
            TriageEscalationReason.SUSPECTED_FRAUD,
            TriageEscalationReason.SAFETY_OR_ABUSE_CONCERN,
        }
    ):
        warnings.append(TriageGuidanceWarning.LOW_WITH_SERIOUS_ESCALATION)
    if (
        fields.issue_category is IssueCategory.OTHER_OR_UNCLEAR
        and fields.recommended_queue
        not in {
            None,
            RecommendedQueue.GENERAL_SUPPORT,
            RecommendedQueue.SPECIALIST_OR_MANUAL_REVIEW,
        }
    ):
        warnings.append(TriageGuidanceWarning.UNCLEAR_TO_SPECIALIST)
    if (
        fields.primary_intent is SupportIntent.REQUEST_REFUND
        and fields.recommended_queue
        not in {
            None,
            RecommendedQueue.REFUNDS_AND_CANCELLATIONS,
            RecommendedQueue.BILLING_OPERATIONS,
        }
    ):
        warnings.append(TriageGuidanceWarning.REFUND_QUEUE_DEPARTURE)
    if (
        (
            fields.primary_intent is SupportIntent.REPORT_TECHNICAL_PROBLEM
            or fields.issue_category is IssueCategory.TECHNICAL_PROBLEM
        )
        and fields.recommended_queue is RecommendedQueue.PRODUCT_FEEDBACK
    ):
        warnings.append(TriageGuidanceWarning.TECHNICAL_TO_FEEDBACK)
    return tuple(warnings)


def validate_final_fields(
    fields: TriageFields,
    *,
    consequential_override: bool = False,
) -> tuple[TriageGuidanceWarning, ...]:
    for name, value in (
        ("primary_intent", fields.primary_intent),
        ("issue_category", fields.issue_category),
        ("urgency", fields.urgency),
        ("recommended_queue", fields.recommended_queue),
        ("primary_next_action", fields.primary_next_action),
    ):
        if value is None:
            raise ValidationError(
                field=name, code="required", message=f"{name} is required."
            )
    needs_unclear = (
        fields.issue_category is IssueCategory.OTHER_OR_UNCLEAR
        or fields.urgency is TriageUrgency.UNCLEAR
    )
    if needs_unclear and not fields.unclear_reason:
        raise ValidationError(
            field="unclear_reason",
            code="required",
            message="Unclear or other classification requires an explanation.",
        )
    warnings = triage_guidance_warnings(fields)
    notes_required = bool(
        needs_unclear
        or fields.escalation_required
        or warnings
        or consequential_override
    )
    if notes_required and not fields.human_notes:
        raise ValidationError(
            field="human_notes",
            code="required",
            message=(
                "Human notes are required for escalation, unclear values, "
                "guidance warnings, or consequential mock overrides."
            ),
        )
    return warnings


@dataclass(frozen=True, slots=True)
class GuideRule:
    rule_id: str
    title: str
    guidance: str


@dataclass(frozen=True, slots=True)
class TriageGuide:
    guide_id: str
    version: str
    name: str
    disclaimer: str
    rules: tuple[GuideRule, ...]

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules)


@dataclass(frozen=True, slots=True)
class TriageContextSnapshot:
    source_record_id: str
    text: str
    excerpted: bool
    excerpt_provenance: str
    trusted_metadata: tuple[tuple[str, str], ...]
    source_label: str
    source_timestamp: str
    sentiment_signal: str
    emotion_signal: str
    human_review: str
    context_notes: tuple[str, ...]
    snapshot_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            clean_text(
                self.text,
                field="source_text",
                limit=MAX_TEXT_LENGTH,
                required=True,
            ),
        )
        object.__setattr__(
            self,
            "snapshot_at",
            require_utc(self.snapshot_at, field="snapshot_at"),
        )


@dataclass(frozen=True, slots=True)
class MockTriageSuggestion:
    fields: TriageFields
    rationale: str
    provider_id: str
    provider_version: str
    provenance: MockProvenance

    def __post_init__(self) -> None:
        if self.provenance is MockProvenance.UNAVAILABLE:
            raise ValidationError(
                field="mock_provenance",
                code="invalid",
                message="Unavailable mock suggestions must be represented as None.",
            )
        validate_final_fields(self.fields)
        object.__setattr__(
            self,
            "rationale",
            clean_text(
                self.rationale,
                field="mock_rationale",
                limit=MAX_NOTE_LENGTH,
                required=True,
            ),
        )


@dataclass(frozen=True, slots=True)
class SupportTicket:
    ticket_id: str
    fixture_version: str
    source: TicketSource
    source_label: str
    complexity: TicketComplexity
    text: str
    guide_id: str
    guide_version: str
    applicable_rule_ids: tuple[str, ...]
    mock_suggestion: MockTriageSuggestion | None
    source_snapshot: TriageContextSnapshot | None = None
    original_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            clean_text(
                self.text,
                field="ticket_text",
                limit=MAX_TEXT_LENGTH,
                required=True,
            ),
        )
        if not self.applicable_rule_ids:
            raise ValidationError(
                field="applicable_rule_ids",
                code="required",
                message="A ticket requires applicable guide rules.",
            )
        if len(self.applicable_rule_ids) != len(set(self.applicable_rule_ids)):
            raise ValidationError(
                field="applicable_rule_ids",
                code="duplicate",
                message="Applicable rule IDs must be unique.",
            )
        if (
            self.source is TicketSource.BUILT_IN_SYNTHETIC
            and self.source_snapshot is not None
        ):
            raise ValidationError(
                field="source_snapshot",
                code="unexpected",
                message="Synthetic tickets cannot contain workspace snapshots.",
            )
        if (
            self.source is TicketSource.WORKSPACE_RECORD
            and self.source_snapshot is None
        ):
            raise ValidationError(
                field="source_snapshot",
                code="required",
                message="Workspace-derived tickets require a frozen snapshot.",
            )


@dataclass(frozen=True, slots=True)
class SavedDraft:
    fields: TriageFields
    saved_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "saved_at",
            require_utc(self.saved_at, field="draft_saved_at"),
        )


@dataclass(frozen=True, slots=True)
class FinalizedTriageDecision:
    fields: TriageFields
    warnings: tuple[TriageGuidanceWarning, ...]
    guide_id: str
    guide_version: str
    applicable_rule_ids: tuple[str, ...]
    finalized_at: datetime
    mock_visible_before_first_submission: bool

    def __post_init__(self) -> None:
        expected = triage_guidance_warnings(self.fields)
        if self.warnings != expected:
            raise ValidationError(
                field="warnings",
                code="mismatch",
                message="Stored warnings must match the finalized decision.",
            )
        object.__setattr__(
            self,
            "finalized_at",
            require_utc(self.finalized_at, field="finalized_at"),
        )


@dataclass(frozen=True, slots=True)
class TicketTriageState:
    ticket: SupportTicket
    draft: SavedDraft | None = None
    first_final: FinalizedTriageDecision | None = None
    final: FinalizedTriageDecision | None = None
    revision_count: int = 0
    mock_revealed: bool = False

    @property
    def status(self) -> TicketStatus:
        if self.final is not None:
            return TicketStatus.FINALIZED
        if self.draft is not None:
            return TicketStatus.DRAFT
        return TicketStatus.UNTRIAGED

    def __post_init__(self) -> None:
        if (self.first_final is None) != (self.final is None):
            raise ValidationError(
                field="final",
                code="inconsistent",
                message="First and current final decisions must coexist.",
            )
        if self.revision_count < 0:
            raise ValidationError(
                field="revision_count",
                code="invalid",
                message="Revision count cannot be negative.",
            )
