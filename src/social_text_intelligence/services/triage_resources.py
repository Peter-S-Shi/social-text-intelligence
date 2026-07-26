"""Load and validate the packaged synthetic support triage resources."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from ..contracts.errors import ValidationError
from ..contracts.triage import (
    GuideRule,
    IssueCategory,
    MockProvenance,
    MockTriageSuggestion,
    NextAction,
    RecommendedQueue,
    SupportIntent,
    SupportTicket,
    TicketComplexity,
    TicketSource,
    TriageEscalationReason,
    TriageFields,
    TriageGuide,
    TriageUrgency,
)

EXPECTED_GUIDE_ID = "sti-synthetic-support-triage-guide"
EXPECTED_GUIDE_VERSION = "1.0.0"
EXPECTED_FIXTURE_VERSION = "1.0.0"
EXPECTED_MOCK_PROVIDER_ID = "sti-fixture-support-triage-mock"
EXPECTED_MOCK_PROVIDER_VERSION = "1.0.0"


def _resource_json(name: str) -> dict[str, Any]:
    package = resources.files("social_text_intelligence.resources")
    data = json.loads(package.joinpath(name).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError(
            field="resource", code="invalid", message=f"{name} must be an object."
        )
    return data


def _enum(
    enum_type: type[Any], value: object, *, field: str
) -> Any:
    try:
        return enum_type(str(value))
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_enum",
            message=f"{field} contains an unsupported value.",
        ) from error


def _fields(data: dict[str, Any]) -> TriageFields:
    return TriageFields(
        primary_intent=_enum(
            SupportIntent, data["primary_intent"], field="primary_intent"
        ),
        secondary_intents=tuple(
            _enum(SupportIntent, value, field="secondary_intents")
            for value in data.get("secondary_intents", [])
        ),
        issue_category=_enum(
            IssueCategory, data["issue_category"], field="issue_category"
        ),
        urgency=_enum(TriageUrgency, data["urgency"], field="urgency"),
        recommended_queue=_enum(
            RecommendedQueue,
            data["recommended_queue"],
            field="recommended_queue",
        ),
        escalation_required=bool(data.get("escalation_required", False)),
        escalation_reason=(
            _enum(
                TriageEscalationReason,
                data["escalation_reason"],
                field="escalation_reason",
            )
            if data.get("escalation_reason")
            else None
        ),
        primary_next_action=_enum(
            NextAction,
            data["primary_next_action"],
            field="primary_next_action",
        ),
        secondary_next_actions=tuple(
            _enum(NextAction, value, field="secondary_next_actions")
            for value in data.get("secondary_next_actions", [])
        ),
        unclear_reason=str(data.get("unclear_reason", "")),
        human_notes=str(data.get("human_notes", "")),
    )


def load_triage_guide() -> TriageGuide:
    data = _resource_json("support_triage_guide_v1.json")
    guide = TriageGuide(
        guide_id=str(data["guide_id"]),
        version=str(data["version"]),
        name=str(data["name"]),
        disclaimer=str(data["disclaimer"]),
        rules=tuple(
            GuideRule(
                rule_id=str(item["rule_id"]),
                title=str(item["title"]),
                guidance=str(item["guidance"]),
            )
            for item in data["rules"]
        ),
    )
    if (
        guide.guide_id != EXPECTED_GUIDE_ID
        or guide.version != EXPECTED_GUIDE_VERSION
    ):
        raise ValidationError(
            field="guide",
            code="unexpected_version",
            message="The packaged support triage guide identity is unexpected.",
        )
    if len(guide.rule_ids) != len(set(guide.rule_ids)):
        raise ValidationError(
            field="guide_rules",
            code="duplicate",
            message="Guide rule IDs must be stable and unique.",
        )
    return guide


def load_support_tickets(
    guide: TriageGuide | None = None,
) -> tuple[SupportTicket, ...]:
    guide = guide or load_triage_guide()
    data = _resource_json("support_triage_tickets_v1.json")
    fixture_version = str(data["fixture_version"])
    if fixture_version != EXPECTED_FIXTURE_VERSION:
        raise ValidationError(
            field="fixture_version",
            code="unexpected_version",
            message="The packaged support ticket version is unexpected.",
        )
    tickets: list[SupportTicket] = []
    for index, item in enumerate(data["tickets"], start=1):
        mock_data = item.get("mock")
        mock = None
        if mock_data is not None:
            mock = MockTriageSuggestion(
                fields=_fields(mock_data),
                rationale=str(mock_data["rationale"]),
                provider_id=EXPECTED_MOCK_PROVIDER_ID,
                provider_version=EXPECTED_MOCK_PROVIDER_VERSION,
                provenance=MockProvenance.BUILT_IN_MOCK,
            )
        ticket = SupportTicket(
            ticket_id=str(item["ticket_id"]),
            fixture_version=fixture_version,
            source=TicketSource.BUILT_IN_SYNTHETIC,
            source_label="built-in synthetic library",
            complexity=_enum(
                TicketComplexity, item["complexity"], field="complexity"
            ),
            text=str(item["text"]),
            guide_id=guide.guide_id,
            guide_version=guide.version,
            applicable_rule_ids=tuple(str(value) for value in item["rule_ids"]),
            mock_suggestion=mock,
            original_order=index,
        )
        unknown = set(ticket.applicable_rule_ids) - set(guide.rule_ids)
        if unknown:
            raise ValidationError(
                field="applicable_rule_ids",
                code="unknown_rule",
                message=f"{ticket.ticket_id} references an unknown guide rule.",
            )
        tickets.append(ticket)
    identities = tuple(ticket.ticket_id for ticket in tickets)
    if len(identities) != len(set(identities)):
        raise ValidationError(
            field="ticket_id",
            code="duplicate",
            message="Synthetic ticket IDs must be unique.",
        )
    if not 20 <= len(tickets) <= 24:
        raise ValidationError(
            field="tickets",
            code="fixture_count",
            message="The synthetic ticket library must contain 20 to 24 tickets.",
        )
    return tuple(tickets)
