"""Services for the bounded local support triage workbench."""

from __future__ import annotations

import csv
import io
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from secrets import token_urlsafe
from typing import Any

from ..contracts.errors import ValidationError
from ..contracts.triage import (
    FieldComparisonState,
    FinalizedTriageDecision,
    IssueCategory,
    MockProvenance,
    MockTriageSuggestion,
    NextAction,
    RecommendedQueue,
    SavedDraft,
    SupportIntent,
    SupportTicket,
    TicketComplexity,
    TicketSource,
    TicketStatus,
    TicketTriageState,
    TriageContextSnapshot,
    TriageEscalationReason,
    TriageFields,
    TriageGuide,
    TriageMode,
    TriageUrgency,
    utc_now,
    validate_final_fields,
)
from .batch import BatchResult, safe_spreadsheet_text
from .insights import InsightState, SampleSizeAssessment, sample_size_assessment
from .review import ReviewState

CORE_COMPARISON_FIELDS = (
    "primary_intent",
    "issue_category",
    "urgency",
    "recommended_queue",
    "escalation_required",
    "primary_next_action",
)
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
class TriageLimits:
    max_tickets: int = 200

    def __post_init__(self) -> None:
        if self.max_tickets < 1:
            raise ValueError("max_tickets must be positive")


@dataclass(frozen=True, slots=True)
class TriageWorkspace:
    mode: TriageMode
    source_batch_token: str | None
    entries: tuple[TicketTriageState, ...]
    created_at: datetime

    def entry(self, ticket_id: str) -> TicketTriageState | None:
        return next(
            (item for item in self.entries if item.ticket.ticket_id == ticket_id),
            None,
        )


@dataclass(frozen=True, slots=True)
class TriageFilter:
    status: TicketStatus | None = None
    source: TicketSource | None = None
    source_label: str = ""
    topic: str = ""
    community: str = ""
    primary_intent: SupportIntent | None = None
    issue_category: IssueCategory | None = None
    urgency: TriageUrgency | None = None
    recommended_queue: RecommendedQueue | None = None
    escalation_required: bool | None = None
    mock_available: bool | None = None
    disagreement: bool | None = None
    guidance_warning: bool | None = None
    text_search: str = ""


@dataclass(frozen=True, slots=True)
class FieldComparison:
    field: str
    human_value: str
    mock_value: str
    state: FieldComparisonState


@dataclass(frozen=True, slots=True)
class TicketComparison:
    fields: tuple[FieldComparison, ...]
    override_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SummaryMetric:
    name: str
    numerator: int
    denominator: int
    excluded: int
    definition: str

    @property
    def rate(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0


@dataclass(frozen=True, slots=True)
class TriageSummary:
    total_eligible: int
    synthetic_count: int
    workspace_count: int
    untriaged_count: int
    draft_count: int
    finalized_count: int
    excluded_count: int
    intent_distribution: tuple[tuple[str, int], ...]
    category_distribution: tuple[tuple[str, int], ...]
    urgency_distribution: tuple[tuple[str, int], ...]
    queue_distribution: tuple[tuple[str, int], ...]
    escalation_count: int
    unclear_count: int
    warning_ticket_count: int
    mock_available_count: int
    follow_up_reasons: tuple[tuple[str, int], ...]
    first_agreement: tuple[SummaryMetric, ...]
    final_agreement: tuple[SummaryMetric, ...]
    first_override_counts: tuple[tuple[str, int], ...]
    final_override_counts: tuple[tuple[str, int], ...]
    mock_visible_before_count: int
    mock_hidden_before_count: int
    sample: SampleSizeAssessment


def new_triage_workspace(
    *,
    mode: TriageMode,
    source_batch_token: str | None = None,
    now: Callable[[], datetime] = utc_now,
) -> TriageWorkspace:
    return TriageWorkspace(
        mode=mode,
        source_batch_token=source_batch_token,
        entries=(),
        created_at=now(),
    )


def _parse_optional(
    enum_type: type[Any], value: str, *, field: str
) -> Any:
    if not value.strip():
        return None
    try:
        return enum_type(value.strip())
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_choice",
            message=f"Select a supported {field}.",
        ) from error


def parse_triage_fields(
    *,
    primary_intent: str,
    secondary_intents: Sequence[str],
    issue_category: str,
    urgency: str,
    recommended_queue: str,
    escalation_required: bool,
    escalation_reason: str,
    primary_next_action: str,
    secondary_next_actions: Sequence[str],
    unclear_reason: str,
    human_notes: str,
) -> TriageFields:
    return TriageFields(
        primary_intent=_parse_optional(
            SupportIntent, primary_intent, field="primary_intent"
        ),
        secondary_intents=tuple(
            _parse_optional(SupportIntent, value, field="secondary_intents")
            for value in secondary_intents
        ),
        issue_category=_parse_optional(
            IssueCategory, issue_category, field="issue_category"
        ),
        urgency=_parse_optional(TriageUrgency, urgency, field="urgency"),
        recommended_queue=_parse_optional(
            RecommendedQueue, recommended_queue, field="recommended_queue"
        ),
        escalation_required=escalation_required,
        escalation_reason=_parse_optional(
            TriageEscalationReason,
            escalation_reason,
            field="escalation_reason",
        ),
        primary_next_action=_parse_optional(
            NextAction, primary_next_action, field="primary_next_action"
        ),
        secondary_next_actions=tuple(
            _parse_optional(NextAction, value, field="secondary_next_actions")
            for value in secondary_next_actions
        ),
        unclear_reason=unclear_reason,
        human_notes=human_notes,
    )


def _replace_entry(
    workspace: TriageWorkspace, replacement: TicketTriageState
) -> TriageWorkspace:
    return replace(
        workspace,
        entries=tuple(
            replacement
            if item.ticket.ticket_id == replacement.ticket.ticket_id
            else item
            for item in workspace.entries
        ),
    )


def add_synthetic_tickets(
    workspace: TriageWorkspace,
    available: Sequence[SupportTicket],
    *,
    ticket_ids: Sequence[str],
    limits: TriageLimits,
) -> TriageWorkspace:
    selected_ids = tuple(dict.fromkeys(ticket_ids))
    available_map = {ticket.ticket_id: ticket for ticket in available}
    existing = {entry.ticket.ticket_id for entry in workspace.entries}
    selected: list[SupportTicket] = []
    for ticket_id in selected_ids:
        ticket = available_map.get(ticket_id)
        if ticket is None:
            raise ValidationError(
                field="ticket_ids",
                code="unknown_ticket",
                message="Select only available synthetic tickets.",
            )
        if ticket_id not in existing:
            selected.append(ticket)
    if len(workspace.entries) + len(selected) > limits.max_tickets:
        raise ValidationError(
            field="tickets",
            code="ticket_limit",
            message=(
                f"This temporary workspace allows at most {limits.max_tickets} "
                "tickets. Export or clear it before adding more."
            ),
        )
    return replace(
        workspace,
        entries=(
            *workspace.entries,
            *(TicketTriageState(ticket=ticket) for ticket in selected),
        ),
    )


def _record_notes(
    insights: InsightState | None,
    *,
    record_id: str,
    topic: str,
    community: str,
    source_label: str,
) -> tuple[str, ...]:
    if insights is None:
        return ()
    notes: list[str] = []
    for note in insights.notes:
        value = note.association_value
        if (
            (note.association.value == "record" and value == record_id)
            or (note.association.value == "topic" and value == topic)
            or (note.association.value == "community" and value == community)
            or (
                note.association.value == "source_label"
                and value == source_label
            )
        ):
            notes.append(
                " | ".join(
                    (
                        note.association.value,
                        value,
                        note.phrase,
                        note.explanation,
                        ",".join(tag.value for tag in note.tags),
                        note.created_at.isoformat(),
                    )
                )
            )
    return tuple(notes)


def prepare_workspace_ticket(
    workspace: TriageWorkspace,
    result: BatchResult,
    reviews: ReviewState | None,
    insights: InsightState | None,
    *,
    record_id: str,
    excerpt: str,
    complexity: TicketComplexity,
    guide: TriageGuide,
    applicable_rule_ids: Sequence[str],
    mock_suggestion: MockTriageSuggestion | None,
    limits: TriageLimits,
    now: Callable[[], datetime] = utc_now,
    ticket_id_factory: Callable[[], str] = lambda: token_urlsafe(10),
) -> TriageWorkspace:
    if len(workspace.entries) >= limits.max_tickets:
        raise ValidationError(
            field="tickets",
            code="ticket_limit",
            message=(
                f"This temporary workspace allows at most {limits.max_tickets} "
                "tickets. Export or clear it before adding more."
            ),
        )
    outcome = next(
        (
            item
            for item in result.outcomes
            if item.prepared.identity == record_id
            and item.prepared.record is not None
        ),
        None,
    )
    if outcome is None or outcome.prepared.record is None:
        raise ValidationError(
            field="record_id",
            code="not_eligible",
            message=(
                "Only successfully parsed source records are eligible. NLP "
                "analysis success is not required."
            ),
        )
    record = outcome.prepared.record
    source_text = record.text
    selected = excerpt.replace("\r\n", "\n").replace("\r", "\n").strip()
    if selected:
        if len(selected) > 4_000 or selected not in source_text:
            raise ValidationError(
                field="excerpt",
                code="invalid_excerpt",
                message=(
                    "A triage excerpt must be a literal bounded excerpt of the "
                    "source record."
                ),
            )
        ticket_text = selected
        excerpted = selected != source_text
    else:
        ticket_text = source_text
        excerpted = False
    rule_ids = tuple(dict.fromkeys(applicable_rule_ids))
    if not rule_ids or not set(rule_ids) <= set(guide.rule_ids):
        raise ValidationError(
            field="applicable_rule_ids",
            code="invalid_rules",
            message="Select at least one valid routing-guide rule.",
        )
    review_text = ""
    if reviews is not None:
        review = reviews.for_record(record_id)
        if review is not None:
            review_text = " | ".join(
                (
                    "reviewed" if review.is_reviewed else "partial_or_unreviewed",
                    review.sentiment_judgment.value
                    if review.sentiment_judgment
                    else "",
                    review.human_sentiment.value
                    if review.human_sentiment
                    else "",
                    review.emotion_judgment.value
                    if review.emotion_judgment
                    else "",
                    review.human_dominant_emotion.value
                    if review.human_dominant_emotion
                    else "",
                    ",".join(
                        value.value for value in review.human_secondary_emotions
                    ),
                    review.note or "",
                )
            )
    sentiment = ""
    emotion = ""
    if outcome.report is not None:
        report = outcome.report
        sentiment = " | ".join(
            (
                report.sentiment.label.value,
                str(report.sentiment.confidence),
                report.sentiment.provider.model_name,
                report.sentiment.provider.revision,
            )
        )
        emotion = " | ".join(
            (
                report.emotion.dominant_emotion.value,
                ",".join(
                    value.value for value in report.emotion.secondary_emotions
                ),
                str(report.emotion.confidence),
                str(report.emotion.threshold),
                report.emotion.provider.model_name,
                report.emotion.provider.revision,
            )
        )
    metadata = {
        "source_type": record.source_type.value,
        "source_label": record.source_label or "",
        "language": record.language or "",
        "timestamp": record.timestamp.isoformat() if record.timestamp else "",
        "topic": record.topic or "",
        "community": record.community or "",
        "parent_record_id": record.parent_record_id or "",
        "notes": record.notes or "",
    }
    snapshot = TriageContextSnapshot(
        source_record_id=record.record_id,
        text=ticket_text,
        excerpted=excerpted,
        excerpt_provenance=(
            "literal_user_selected_excerpt"
            if excerpted
            else "complete_source_record"
        ),
        trusted_metadata=tuple(
            (field, metadata[field]) for field in TRUSTED_METADATA_FIELDS
        ),
        source_label=record.source_label or "workspace record",
        source_timestamp=metadata["timestamp"],
        sentiment_signal=sentiment,
        emotion_signal=emotion,
        human_review=review_text,
        context_notes=_record_notes(
            insights,
            record_id=record.record_id,
            topic=record.topic or "",
            community=record.community or "",
            source_label=record.source_label or "",
        ),
        snapshot_at=now(),
    )
    ticket = SupportTicket(
        ticket_id=f"workspace-{ticket_id_factory()}",
        fixture_version="workspace-snapshot-v1",
        source=TicketSource.WORKSPACE_RECORD,
        source_label=record.source_label or "workspace record",
        complexity=complexity,
        text=ticket_text,
        guide_id=guide.guide_id,
        guide_version=guide.version,
        applicable_rule_ids=rule_ids,
        mock_suggestion=mock_suggestion,
        source_snapshot=snapshot,
        original_order=len(workspace.entries) + 10_000,
    )
    return replace(
        workspace,
        entries=(*workspace.entries, TicketTriageState(ticket=ticket)),
    )


def save_triage_draft(
    workspace: TriageWorkspace,
    *,
    ticket_id: str,
    fields: TriageFields,
    now: Callable[[], datetime] = utc_now,
) -> TriageWorkspace:
    entry = workspace.entry(ticket_id)
    if entry is None:
        raise ValidationError(
            field="ticket_id", code="not_found", message="Ticket not found."
        )
    if entry.final is not None:
        raise ValidationError(
            field="ticket",
            code="already_finalized",
            message="A finalized ticket cannot return to Draft.",
        )
    return _replace_entry(
        workspace,
        replace(entry, draft=SavedDraft(fields=fields, saved_at=now())),
    )


def _value(fields: TriageFields, name: str) -> str:
    value = getattr(fields, name)
    if isinstance(value, bool):
        return str(value).lower()
    return value.value if value is not None else ""


def compare_to_mock(
    fields: TriageFields, suggestion: MockTriageSuggestion | None
) -> TicketComparison:
    comparisons: list[FieldComparison] = []
    overrides: list[str] = []
    for field in CORE_COMPARISON_FIELDS:
        human_value = _value(fields, field)
        if suggestion is None:
            state = FieldComparisonState.UNAVAILABLE
            mock_value = ""
        else:
            mock_value = _value(suggestion.fields, field)
            state = (
                FieldComparisonState.AGREE
                if human_value == mock_value
                else FieldComparisonState.OVERRIDE
            )
            if state is FieldComparisonState.OVERRIDE:
                overrides.append(field)
        comparisons.append(
            FieldComparison(
                field=field,
                human_value=human_value,
                mock_value=mock_value,
                state=state,
            )
        )
    return TicketComparison(
        fields=tuple(comparisons), override_fields=tuple(overrides)
    )


def _finalize(
    entry: TicketTriageState,
    fields: TriageFields,
    *,
    mode: TriageMode,
    first_submission: bool,
    now: Callable[[], datetime],
) -> FinalizedTriageDecision:
    mock_visible = mode is TriageMode.MOCK_ASSISTED
    comparison = compare_to_mock(fields, entry.ticket.mock_suggestion)
    consequential = bool(
        mock_visible
        and {
            "urgency",
            "recommended_queue",
            "escalation_required",
        }
        & set(comparison.override_fields)
    )
    warnings = validate_final_fields(
        fields, consequential_override=consequential
    )
    if (
        entry.ticket.guide_id == ""
        or entry.ticket.guide_version == ""
        or not entry.ticket.applicable_rule_ids
    ):
        raise ValidationError(
            field="guide",
            code="missing_provenance",
            message="Frozen guide provenance is required.",
        )
    return FinalizedTriageDecision(
        fields=fields,
        warnings=warnings,
        guide_id=entry.ticket.guide_id,
        guide_version=entry.ticket.guide_version,
        applicable_rule_ids=entry.ticket.applicable_rule_ids,
        finalized_at=now(),
        mock_visible_before_first_submission=(
            mock_visible
            if first_submission
            else bool(
                entry.first_final
                and entry.first_final.mock_visible_before_first_submission
            )
        ),
    )


def finalize_ticket(
    workspace: TriageWorkspace,
    *,
    ticket_id: str,
    fields: TriageFields,
    now: Callable[[], datetime] = utc_now,
) -> TriageWorkspace:
    entry = workspace.entry(ticket_id)
    if entry is None:
        raise ValidationError(
            field="ticket_id", code="not_found", message="Ticket not found."
        )
    if entry.final is not None:
        raise ValidationError(
            field="ticket",
            code="already_finalized",
            message="Use explicit revision for a finalized ticket.",
        )
    decision = _finalize(
        entry, fields, mode=workspace.mode, first_submission=True, now=now
    )
    return _replace_entry(
        workspace,
        replace(
            entry,
            draft=None,
            first_final=decision,
            final=decision,
        ),
    )


def revise_ticket(
    workspace: TriageWorkspace,
    *,
    ticket_id: str,
    fields: TriageFields,
    now: Callable[[], datetime] = utc_now,
) -> TriageWorkspace:
    entry = workspace.entry(ticket_id)
    if entry is None or entry.final is None or entry.first_final is None:
        raise ValidationError(
            field="ticket",
            code="not_finalized",
            message="Only a finalized ticket can be revised.",
        )
    decision = _finalize(
        entry, fields, mode=workspace.mode, first_submission=False, now=now
    )
    return _replace_entry(
        workspace,
        replace(
            entry,
            final=decision,
            revision_count=entry.revision_count + 1,
        ),
    )


def reveal_ticket_mock(
    workspace: TriageWorkspace, *, ticket_id: str
) -> TriageWorkspace:
    entry = workspace.entry(ticket_id)
    if entry is None:
        raise ValidationError(
            field="ticket", code="not_found", message="Ticket not found."
        )
    if workspace.mode is not TriageMode.INDEPENDENT:
        return workspace
    if entry.first_final is None:
        raise ValidationError(
            field="mock",
            code="hidden_before_finalize",
            message="Independent mode keeps the mock hidden until first finalize.",
        )
    return _replace_entry(workspace, replace(entry, mock_revealed=True))


def mock_is_visible(
    workspace: TriageWorkspace, entry: TicketTriageState
) -> bool:
    return bool(
        entry.ticket.mock_suggestion is not None
        and (
            workspace.mode is TriageMode.MOCK_ASSISTED
            or entry.mock_revealed
        )
    )


def _metadata(entry: TicketTriageState) -> Mapping[str, str]:
    snapshot = entry.ticket.source_snapshot
    return dict(snapshot.trusted_metadata) if snapshot is not None else {}


def filter_triage_entries(
    workspace: TriageWorkspace,
    filters: TriageFilter,
    *,
    sort_by: str = "original",
) -> tuple[TicketTriageState, ...]:
    search = filters.text_search.casefold().strip()

    def matches(entry: TicketTriageState) -> bool:
        final = entry.final.fields if entry.final is not None else None
        metadata = _metadata(entry)
        comparison = (
            compare_to_mock(final, entry.ticket.mock_suggestion)
            if final is not None
            else None
        )
        return bool(
            (filters.status is None or entry.status is filters.status)
            and (
                filters.source is None or entry.ticket.source is filters.source
            )
            and (
                not filters.source_label
                or filters.source_label.casefold()
                in entry.ticket.source_label.casefold()
            )
            and (
                not filters.topic
                or metadata.get("topic", "") == filters.topic
            )
            and (
                not filters.community
                or metadata.get("community", "") == filters.community
            )
            and (
                filters.primary_intent is None
                or (
                    final is not None
                    and final.primary_intent is filters.primary_intent
                )
            )
            and (
                filters.issue_category is None
                or (
                    final is not None
                    and final.issue_category is filters.issue_category
                )
            )
            and (
                filters.urgency is None
                or (final is not None and final.urgency is filters.urgency)
            )
            and (
                filters.recommended_queue is None
                or (
                    final is not None
                    and final.recommended_queue is filters.recommended_queue
                )
            )
            and (
                filters.escalation_required is None
                or (
                    final is not None
                    and final.escalation_required
                    is filters.escalation_required
                )
            )
            and (
                filters.mock_available is None
                or (entry.ticket.mock_suggestion is not None)
                is filters.mock_available
            )
            and (
                filters.disagreement is None
                or (
                    comparison is not None
                    and bool(comparison.override_fields)
                    is filters.disagreement
                )
            )
            and (
                filters.guidance_warning is None
                or (
                    entry.final is not None
                    and bool(entry.final.warnings)
                    is filters.guidance_warning
                )
            )
            and (not search or search in entry.ticket.text.casefold())
        )

    entries = [entry for entry in workspace.entries if matches(entry)]
    urgency_rank = {
        None: 5,
        TriageUrgency.CRITICAL: 0,
        TriageUrgency.HIGH: 1,
        TriageUrgency.NORMAL: 2,
        TriageUrgency.LOW: 3,
        TriageUrgency.UNCLEAR: 4,
    }
    if sort_by == "urgency":
        entries.sort(
            key=lambda item: (
                urgency_rank[
                    item.final.fields.urgency if item.final is not None else None
                ],
                item.ticket.original_order,
            )
        )
    elif sort_by == "status":
        entries.sort(key=lambda item: (item.status.value, item.ticket.original_order))
    elif sort_by == "timestamp":
        entries.sort(
            key=lambda item: (
                item.ticket.source_snapshot.source_timestamp
                if item.ticket.source_snapshot
                else "",
                item.ticket.original_order,
            )
        )
    else:
        entries.sort(key=lambda item: item.ticket.original_order)
    return tuple(entries)


def _distribution(
    finalized: Sequence[TicketTriageState], field: str
) -> tuple[tuple[str, int], ...]:
    values = Counter(
        _value(entry.final.fields, field)
        for entry in finalized
        if entry.final is not None
    )
    return tuple(sorted(values.items()))


def _agreement_metrics(
    finalized: Sequence[TicketTriageState], *, first: bool
) -> tuple[SummaryMetric, ...]:
    metrics: list[SummaryMetric] = []
    for field in CORE_COMPARISON_FIELDS:
        eligible = 0
        agree = 0
        for entry in finalized:
            decision = entry.first_final if first else entry.final
            if decision is None or entry.ticket.mock_suggestion is None:
                continue
            eligible += 1
            comparison = compare_to_mock(
                decision.fields, entry.ticket.mock_suggestion
            )
            state = next(
                item.state for item in comparison.fields if item.field == field
            )
            agree += state is FieldComparisonState.AGREE
        metrics.append(
            SummaryMetric(
                name=field,
                numerator=agree,
                denominator=eligible,
                excluded=len(finalized) - eligible,
                definition=(
                    "Human and available deterministic mock have the same "
                    f"{field}; descriptive agreement, not accuracy."
                ),
            )
        )
    return tuple(metrics)


def _override_counts(
    finalized: Sequence[TicketTriageState], *, first: bool
) -> tuple[tuple[str, int], ...]:
    counts = Counter({field: 0 for field in CORE_COMPARISON_FIELDS})
    for entry in finalized:
        decision = entry.first_final if first else entry.final
        if decision is None or entry.ticket.mock_suggestion is None:
            continue
        comparison = compare_to_mock(
            decision.fields, entry.ticket.mock_suggestion
        )
        counts.update(comparison.override_fields)
    return tuple((field, counts[field]) for field in CORE_COMPARISON_FIELDS)


def summarize_triage(workspace: TriageWorkspace) -> TriageSummary:
    entries = workspace.entries
    finalized = tuple(entry for entry in entries if entry.final is not None)
    follow: Counter[str] = Counter()
    for entry in finalized:
        assert entry.final is not None
        fields = entry.final.fields
        comparison = compare_to_mock(fields, entry.ticket.mock_suggestion)
        if fields.escalation_required:
            follow["escalation_required"] += 1
        if fields.urgency is TriageUrgency.CRITICAL:
            follow["critical_urgency"] += 1
        if (
            fields.urgency is TriageUrgency.UNCLEAR
            or fields.issue_category is IssueCategory.OTHER_OR_UNCLEAR
        ):
            follow["unclear_category_or_urgency"] += 1
        if fields.primary_next_action is NextAction.REQUEST_MORE_INFORMATION:
            follow["request_more_information"] += 1
        if entry.final.warnings:
            follow["guidance_warning"] += 1
        if entry.ticket.mock_suggestion is None:
            follow["mock_unavailable"] += 1
        for field, name in (
            ("recommended_queue", "queue_disagreement"),
            ("urgency", "urgency_disagreement"),
            ("escalation_required", "escalation_disagreement"),
        ):
            if field in comparison.override_fields:
                follow[name] += 1
    return TriageSummary(
        total_eligible=len(entries),
        synthetic_count=sum(
            entry.ticket.source is TicketSource.BUILT_IN_SYNTHETIC
            for entry in entries
        ),
        workspace_count=sum(
            entry.ticket.source is TicketSource.WORKSPACE_RECORD
            for entry in entries
        ),
        untriaged_count=sum(
            entry.status is TicketStatus.UNTRIAGED for entry in entries
        ),
        draft_count=sum(entry.status is TicketStatus.DRAFT for entry in entries),
        finalized_count=len(finalized),
        excluded_count=len(entries) - len(finalized),
        intent_distribution=_distribution(finalized, "primary_intent"),
        category_distribution=_distribution(finalized, "issue_category"),
        urgency_distribution=_distribution(finalized, "urgency"),
        queue_distribution=_distribution(finalized, "recommended_queue"),
        escalation_count=sum(
            bool(entry.final and entry.final.fields.escalation_required)
            for entry in finalized
        ),
        unclear_count=sum(
            bool(
                entry.final
                and (
                    entry.final.fields.urgency is TriageUrgency.UNCLEAR
                    or entry.final.fields.issue_category
                    is IssueCategory.OTHER_OR_UNCLEAR
                )
            )
            for entry in finalized
        ),
        warning_ticket_count=sum(
            bool(entry.final and entry.final.warnings) for entry in finalized
        ),
        mock_available_count=sum(
            entry.ticket.mock_suggestion is not None for entry in entries
        ),
        follow_up_reasons=tuple(sorted(follow.items())),
        first_agreement=_agreement_metrics(finalized, first=True),
        final_agreement=_agreement_metrics(finalized, first=False),
        first_override_counts=_override_counts(finalized, first=True),
        final_override_counts=_override_counts(finalized, first=False),
        mock_visible_before_count=sum(
            bool(
                entry.first_final
                and entry.first_final.mock_visible_before_first_submission
            )
            for entry in finalized
        ),
        mock_hidden_before_count=sum(
            bool(
                entry.first_final
                and not entry.first_final.mock_visible_before_first_submission
            )
            for entry in finalized
        ),
        sample=sample_size_assessment(len(entries)),
    )


def _fields_cell(fields: TriageFields | None) -> str:
    if fields is None:
        return ""
    values = (
        ("primary_intent", _value(fields, "primary_intent")),
        (
            "secondary_intents",
            ",".join(item.value for item in fields.secondary_intents),
        ),
        ("issue_category", _value(fields, "issue_category")),
        ("urgency", _value(fields, "urgency")),
        ("recommended_queue", _value(fields, "recommended_queue")),
        ("escalation_required", _value(fields, "escalation_required")),
        ("escalation_reason", _value(fields, "escalation_reason")),
        ("primary_next_action", _value(fields, "primary_next_action")),
        (
            "secondary_next_actions",
            ",".join(item.value for item in fields.secondary_next_actions),
        ),
        ("unclear_reason", fields.unclear_reason),
        ("human_notes", fields.human_notes),
    )
    return "; ".join(f"{key}={value}" for key, value in values)


def export_triage_csv(
    workspace: TriageWorkspace,
    *,
    include_source_text: bool = False,
    include_signals: bool = False,
    include_human_review: bool = False,
    include_context_notes: bool = False,
    include_trusted_metadata: bool = False,
    now: Callable[[], datetime] = utc_now,
) -> str:
    summary = summarize_triage(workspace)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        (
            "row_type",
            "exported_at",
            "metric_definition",
            "numerator",
            "denominator",
            "exclusions",
            "sample_status",
            "sample_warning",
            "ticket_id",
            "source_provenance",
            "source_label",
            "ticket_complexity",
            "ticket_status",
            "source_text",
            "trusted_metadata",
            "sentiment_signal",
            "emotion_signal",
            "human_review",
            "context_notes",
            "guide_id",
            "guide_version",
            "applicable_rule_ids",
            "draft_fields",
            "draft_saved_at",
            "first_final_fields",
            "first_final_at",
            "final_fields",
            "final_at",
            "revision_count",
            "first_warnings",
            "final_warnings",
            "mock_available",
            "mock_provenance",
            "mock_provider_id",
            "mock_provider_version",
            "mock_suggestion",
            "mock_rationale",
            "mock_visible_before_first_submission",
            "first_field_comparison",
            "final_field_comparison",
            "first_override_fields",
            "final_override_fields",
        )
    )
    exported_at = now().astimezone(UTC).isoformat()
    writer.writerow(
        (
            "export_metadata",
            exported_at,
            (
                "Finalized distributions exclude untriaged and draft tickets. "
                "Mock comparisons exclude unavailable mocks. Percentages use "
                "each metric's disclosed denominator."
            ),
            summary.finalized_count,
            summary.total_eligible,
            summary.excluded_count,
            summary.sample.level.value,
            summary.sample.message or "",
            *("" for _ in range(34)),
        )
    )
    for metric in (*summary.first_agreement, *summary.final_agreement):
        writer.writerow(
            (
                "summary_metric",
                exported_at,
                metric.definition,
                metric.numerator,
                metric.denominator,
                metric.excluded,
                summary.sample.level.value,
                summary.sample.message or "",
                metric.name,
                *("" for _ in range(33)),
            )
        )
    for entry in workspace.entries:
        ticket = entry.ticket
        snapshot = ticket.source_snapshot
        workspace_source = ticket.source is TicketSource.WORKSPACE_RECORD
        source_text = (
            ticket.text
            if not workspace_source or include_source_text
            else ""
        )
        metadata = (
            "; ".join(f"{key}={value}" for key, value in snapshot.trusted_metadata)
            if snapshot is not None and include_trusted_metadata
            else ""
        )
        sentiment = (
            snapshot.sentiment_signal
            if snapshot is not None and include_signals
            else ""
        )
        emotion = (
            snapshot.emotion_signal
            if snapshot is not None and include_signals
            else ""
        )
        review = (
            snapshot.human_review
            if snapshot is not None and include_human_review
            else ""
        )
        notes = (
            " || ".join(snapshot.context_notes)
            if snapshot is not None and include_context_notes
            else ""
        )
        first_comparison = (
            compare_to_mock(entry.first_final.fields, ticket.mock_suggestion)
            if entry.first_final is not None
            else None
        )
        final_comparison = (
            compare_to_mock(entry.final.fields, ticket.mock_suggestion)
            if entry.final is not None
            else None
        )

        def comparison_cell(comparison: TicketComparison | None) -> str:
            return (
                "; ".join(
                    f"{item.field}={item.state.value}"
                    for item in comparison.fields
                )
                if comparison is not None
                else ""
            )

        mock = ticket.mock_suggestion
        user_cells = (
            source_text,
            metadata,
            sentiment,
            emotion,
            review,
            notes,
            _fields_cell(entry.draft.fields if entry.draft else None),
            _fields_cell(entry.first_final.fields if entry.first_final else None),
            _fields_cell(entry.final.fields if entry.final else None),
            _fields_cell(mock.fields if mock else None),
            mock.rationale if mock else "",
        )
        safe = tuple(safe_spreadsheet_text(value) for value in user_cells)
        writer.writerow(
            (
                "ticket",
                exported_at,
                "",
                "",
                "",
                "",
                summary.sample.level.value,
                summary.sample.message or "",
                ticket.ticket_id,
                ticket.source.value,
                ticket.source_label,
                ticket.complexity.value,
                entry.status.value,
                safe[0],
                safe[1],
                safe[2],
                safe[3],
                safe[4],
                safe[5],
                ticket.guide_id,
                ticket.guide_version,
                ",".join(ticket.applicable_rule_ids),
                safe[6],
                entry.draft.saved_at.isoformat() if entry.draft else "",
                safe[7],
                (
                    entry.first_final.finalized_at.isoformat()
                    if entry.first_final
                    else ""
                ),
                safe[8],
                entry.final.finalized_at.isoformat() if entry.final else "",
                entry.revision_count,
                (
                    ",".join(item.value for item in entry.first_final.warnings)
                    if entry.first_final
                    else ""
                ),
                (
                    ",".join(item.value for item in entry.final.warnings)
                    if entry.final
                    else ""
                ),
                str(mock is not None).lower(),
                mock.provenance.value if mock else MockProvenance.UNAVAILABLE.value,
                mock.provider_id if mock else "",
                mock.provider_version if mock else "",
                safe[9],
                safe[10],
                (
                    str(
                        entry.first_final.mock_visible_before_first_submission
                    ).lower()
                    if entry.first_final
                    else ""
                ),
                comparison_cell(first_comparison),
                comparison_cell(final_comparison),
                (
                    ",".join(first_comparison.override_fields)
                    if first_comparison
                    else ""
                ),
                (
                    ",".join(final_comparison.override_fields)
                    if final_comparison
                    else ""
                ),
            )
        )
    return output.getvalue()
