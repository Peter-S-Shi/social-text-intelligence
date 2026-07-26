"""Load and validate versioned synthetic moderation policy and case resources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from typing import Any, TypeVar

from ..contracts import (
    AmbiguityLevel,
    CaseDifficulty,
    EscalationReason,
    LearningObjective,
    MockModerationRecommendation,
    ModerationCaseSource,
    ModerationDisposition,
    ModerationJudgment,
    ModerationPolicy,
    ModerationSeverity,
    ModerationTrainingCase,
    PolicyCategory,
    PolicyClause,
    PolicySourceType,
    ReferenceDecision,
    ReferenceProvenance,
    UnclearReason,
    ViolationCategory,
)
from ..contracts.errors import ValidationError

EXPECTED_POLICY_ID = "sti-synthetic-moderation-training-policy"
EXPECTED_POLICY_VERSION = "1.0.0"
EXPECTED_FIXTURE_VERSION = "1.0.0"
EXPECTED_MOCK_PROVIDER_ID = "sti-fixture-moderation-mock"
EXPECTED_MOCK_PROVIDER_VERSION = "1.0.0"
EnumValue = TypeVar("EnumValue", bound=StrEnum)


@dataclass(frozen=True, slots=True)
class FixtureCoverage:
    case_count: int
    categories: frozenset[ViolationCategory]
    difficulties: frozenset[CaseDifficulty]
    objectives: frozenset[LearningObjective]
    dispositions: frozenset[ModerationDisposition]
    severities: frozenset[ModerationSeverity]
    escalation_cases: int
    non_escalation_cases: int
    acceptable_alternative_cases: int
    ai_available_cases: int
    ai_unavailable_cases: int
    safety_sensitive_cases: int


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(
            field=field,
            code="invalid_resource",
            message=f"{field} must be an object.",
        )
    return {str(key): item for key, item in value.items()}


def _sequence(value: Any, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(
            field=field,
            code="invalid_resource",
            message=f"{field} must be a list.",
        )
    return value


def _string(
    value: Any, *, field: str, allow_blank: bool = False
) -> str:
    if not isinstance(value, str) or (not allow_blank and not value.strip()):
        raise ValidationError(
            field=field,
            code="invalid_resource",
            message=f"{field} must be a string.",
        )
    return value


def _boolean(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(
            field=field,
            code="invalid_resource",
            message=f"{field} must be true or false.",
        )
    return value


def _enum_value(
    enum_type: type[EnumValue], value: Any, *, field: str
) -> EnumValue:
    try:
        return enum_type(_string(value, field=field))
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_resource_enum",
            message=f"{field} contains an unsupported value.",
        ) from error


def _string_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    return tuple(
        _string(item, field=field)
        for item in _sequence(value, field=field)
    )


def _judgment(value: Any, *, field: str) -> ModerationJudgment:
    item = _mapping(value, field=field)
    return ModerationJudgment(
        disposition=_enum_value(
            ModerationDisposition,
            item.get("disposition"),
            field=f"{field}.disposition",
        ),
        primary_violation=_enum_value(
            ViolationCategory,
            item.get("primary_violation"),
            field=f"{field}.primary_violation",
        ),
        secondary_violations=tuple(
            _enum_value(
                ViolationCategory,
                entry,
                field=f"{field}.secondary_violations",
            )
            for entry in _sequence(
                item.get("secondary_violations", []),
                field=f"{field}.secondary_violations",
            )
        ),
        severity=_enum_value(
            ModerationSeverity,
            item.get("severity"),
            field=f"{field}.severity",
        ),
        escalate=_boolean(
            item.get("escalate"), field=f"{field}.escalate"
        ),
        escalation_reason=(
            _enum_value(
                EscalationReason,
                item["escalation_reason"],
                field=f"{field}.escalation_reason",
            )
            if item.get("escalation_reason")
            else None
        ),
        unclear_reasons=tuple(
            _enum_value(
                UnclearReason,
                entry,
                field=f"{field}.unclear_reasons",
            )
            for entry in _sequence(
                item.get("unclear_reasons", []),
                field=f"{field}.unclear_reasons",
            )
        ),
    )


def _reference(value: Any, *, field: str) -> ReferenceDecision:
    item = _mapping(value, field=field)
    return ReferenceDecision(
        preferred=_judgment(
            item.get("preferred"), field=f"{field}.preferred"
        ),
        acceptable_alternatives=tuple(
            _judgment(entry, field=f"{field}.acceptable_alternatives")
            for entry in _sequence(
                item.get("acceptable_alternatives", []),
                field=f"{field}.acceptable_alternatives",
            )
        ),
        rationale=_string(
            item.get("rationale"), field=f"{field}.rationale"
        ),
        policy_clause_ids=_string_tuple(
            item.get("policy_clause_ids", []),
            field=f"{field}.policy_clause_ids",
        ),
        provenance=ReferenceProvenance.BUILT_IN,
    )


def load_moderation_policy() -> ModerationPolicy:
    raw = json.loads(
        resources.files("social_text_intelligence.resources")
        .joinpath("moderation_policy_v1.json")
        .read_text(encoding="utf-8")
    )
    data = _mapping(raw, field="policy")
    categories: list[PolicyCategory] = []
    clause_ids: set[str] = set()
    for raw_category in _sequence(
        data.get("categories"), field="policy.categories"
    ):
        category = _mapping(raw_category, field="policy.category")
        clauses: list[PolicyClause] = []
        for raw_clause in _sequence(
            category.get("clauses"), field="policy.category.clauses"
        ):
            clause = _mapping(raw_clause, field="policy.clause")
            clause_id = _string(
                clause.get("clause_id"), field="policy.clause.clause_id"
            )
            if clause_id in clause_ids:
                raise ValidationError(
                    field="policy.clause_id",
                    code="duplicate_clause",
                    message="Policy clause IDs must be unique.",
                )
            clause_ids.add(clause_id)
            clauses.append(
                PolicyClause(
                    clause_id=clause_id,
                    text=_string(
                        clause.get("text"), field="policy.clause.text"
                    ),
                )
            )
        categories.append(
            PolicyCategory(
                category_id=_enum_value(
                    ViolationCategory,
                    category.get("category_id"),
                    field="policy.category.category_id",
                ),
                display_name=_string(
                    category.get("display_name"),
                    field="policy.category.display_name",
                ),
                definition=_string(
                    category.get("definition"),
                    field="policy.category.definition",
                ),
                included_examples=_string_tuple(
                    category.get("included_examples"),
                    field="policy.category.included_examples",
                ),
                excluded_examples=_string_tuple(
                    category.get("excluded_examples"),
                    field="policy.category.excluded_examples",
                ),
                severity_guidance=_string(
                    category.get("severity_guidance"),
                    field="policy.category.severity_guidance",
                ),
                disposition_guidance=_string(
                    category.get("disposition_guidance"),
                    field="policy.category.disposition_guidance",
                ),
                escalation_triggers=_string_tuple(
                    category.get("escalation_triggers"),
                    field="policy.category.escalation_triggers",
                ),
                clauses=tuple(clauses),
            )
        )
    policy = ModerationPolicy(
        policy_id=_string(data.get("policy_id"), field="policy.policy_id"),
        policy_version=_string(
            data.get("policy_version"), field="policy.policy_version"
        ),
        name=_string(data.get("name"), field="policy.name"),
        source_type=_enum_value(
            PolicySourceType,
            data.get("source_type"),
            field="policy.source_type",
        ),
        categories=tuple(categories),
    )
    expected_categories = set(ViolationCategory) - {
        ViolationCategory.NO_VIOLATION
    }
    actual_categories = {item.category_id for item in policy.categories}
    if (
        policy.policy_id != EXPECTED_POLICY_ID
        or policy.policy_version != EXPECTED_POLICY_VERSION
        or actual_categories != expected_categories
        or len(actual_categories) != len(policy.categories)
    ):
        raise ValidationError(
            field="policy",
            code="invalid_policy_contract",
            message="The built-in synthetic policy contract is incomplete.",
        )
    return policy


def load_moderation_cases(
    policy: ModerationPolicy | None = None,
) -> tuple[ModerationTrainingCase, ...]:
    selected_policy = policy or load_moderation_policy()
    raw = json.loads(
        resources.files("social_text_intelligence.resources")
        .joinpath("moderation_cases_v1.json")
        .read_text(encoding="utf-8")
    )
    data = _mapping(raw, field="fixtures")
    fixture_version = _string(
        data.get("fixture_version"), field="fixtures.fixture_version"
    )
    policy_id = _string(
        data.get("policy_id"), field="fixtures.policy_id"
    )
    policy_version = _string(
        data.get("policy_version"), field="fixtures.policy_version"
    )
    provider_id = _string(
        data.get("mock_provider_id"), field="fixtures.mock_provider_id"
    )
    provider_version = _string(
        data.get("mock_provider_version"),
        field="fixtures.mock_provider_version",
    )
    if (
        fixture_version != EXPECTED_FIXTURE_VERSION
        or policy_id != selected_policy.policy_id
        or policy_version != selected_policy.policy_version
        or provider_id != EXPECTED_MOCK_PROVIDER_ID
        or provider_version != EXPECTED_MOCK_PROVIDER_VERSION
    ):
        raise ValidationError(
            field="fixtures",
            code="fixture_provenance_mismatch",
            message="Synthetic fixture provenance does not match the policy.",
        )
    valid_clause_ids = {
        clause.clause_id
        for category in selected_policy.categories
        for clause in category.clauses
    }
    cases: list[ModerationTrainingCase] = []
    seen_ids: set[str] = set()
    for order, raw_case in enumerate(
        _sequence(data.get("cases"), field="fixtures.cases"), start=1
    ):
        item = _mapping(raw_case, field="fixture.case")
        case_id = _string(item.get("case_id"), field="fixture.case_id")
        if case_id in seen_ids:
            raise ValidationError(
                field="fixture.case_id",
                code="duplicate_case",
                message="Built-in case IDs must be unique.",
            )
        seen_ids.add(case_id)
        reference = _reference(
            item.get("reference"), field=f"fixture.{case_id}.reference"
        )
        if not set(reference.policy_clause_ids) <= valid_clause_ids:
            raise ValidationError(
                field="policy_clause_ids",
                code="unknown_clause",
                message="A fixture references an unknown policy clause.",
            )
        raw_mock = item.get("mock")
        mock = None
        if raw_mock is not None:
            mock_item = _mapping(
                raw_mock, field=f"fixture.{case_id}.mock"
            )
            mock = MockModerationRecommendation(
                judgment=_judgment(
                    mock_item.get("judgment"),
                    field=f"fixture.{case_id}.mock.judgment",
                ),
                rationale=_string(
                    mock_item.get("rationale"),
                    field=f"fixture.{case_id}.mock.rationale",
                ),
                provider_id=provider_id,
                provider_version=provider_version,
            )
        cases.append(
            ModerationTrainingCase(
                case_id=case_id,
                fixture_version=fixture_version,
                source=ModerationCaseSource.BUILT_IN_SYNTHETIC,
                policy_id=policy_id,
                policy_version=policy_version,
                difficulty=_enum_value(
                    CaseDifficulty,
                    item.get("difficulty"),
                    field=f"fixture.{case_id}.difficulty",
                ),
                topic=_string(
                    item.get("topic"), field=f"fixture.{case_id}.topic"
                ),
                categories_involved=tuple(
                    _enum_value(
                        ViolationCategory,
                        entry,
                        field=f"fixture.{case_id}.categories_involved",
                    )
                    for entry in _sequence(
                        item.get("categories_involved", []),
                        field=f"fixture.{case_id}.categories_involved",
                    )
                ),
                context_available=_boolean(
                    item.get("context_available"),
                    field=f"fixture.{case_id}.context_available",
                ),
                ambiguity_level=_enum_value(
                    AmbiguityLevel,
                    item.get("ambiguity_level"),
                    field=f"fixture.{case_id}.ambiguity_level",
                ),
                safety_sensitive=_boolean(
                    item.get("safety_sensitive"),
                    field=f"fixture.{case_id}.safety_sensitive",
                ),
                learning_objective=_enum_value(
                    LearningObjective,
                    item.get("learning_objective"),
                    field=f"fixture.{case_id}.learning_objective",
                ),
                text=_string(
                    item.get("text"), field=f"fixture.{case_id}.text"
                ),
                context=_string(
                    item.get("context"),
                    field=f"fixture.{case_id}.context",
                    allow_blank=True,
                ),
                reference=reference,
                mock_recommendation=mock,
                original_order=order,
            )
        )
    audit_fixture_coverage(tuple(cases))
    return tuple(cases)


def audit_fixture_coverage(
    cases: tuple[ModerationTrainingCase, ...],
) -> FixtureCoverage:
    references = tuple(
        item.reference for item in cases if item.reference is not None
    )
    coverage = FixtureCoverage(
        case_count=len(cases),
        categories=frozenset(
            category
            for item in cases
            for category in item.categories_involved
            if category is not ViolationCategory.NO_VIOLATION
        ),
        difficulties=frozenset(item.difficulty for item in cases),
        objectives=frozenset(item.learning_objective for item in cases),
        dispositions=frozenset(
            reference.preferred.disposition for reference in references
        ),
        severities=frozenset(
            reference.preferred.severity for reference in references
        ),
        escalation_cases=sum(
            reference.preferred.escalate for reference in references
        ),
        non_escalation_cases=sum(
            not reference.preferred.escalate for reference in references
        ),
        acceptable_alternative_cases=sum(
            bool(reference.acceptable_alternatives)
            for reference in references
        ),
        ai_available_cases=sum(
            item.mock_recommendation is not None for item in cases
        ),
        ai_unavailable_cases=sum(
            item.mock_recommendation is None for item in cases
        ),
        safety_sensitive_cases=sum(item.safety_sensitive for item in cases),
    )
    required_categories = set(ViolationCategory) - {
        ViolationCategory.NO_VIOLATION
    }
    if (
        coverage.case_count < 20
        or coverage.categories != required_categories
        or coverage.difficulties != frozenset(CaseDifficulty)
        or coverage.objectives != frozenset(LearningObjective)
        or coverage.dispositions != frozenset(ModerationDisposition)
        or coverage.severities != frozenset(ModerationSeverity)
        or not coverage.escalation_cases
        or not coverage.non_escalation_cases
        or not coverage.acceptable_alternative_cases
        or not coverage.ai_available_cases
        or not coverage.ai_unavailable_cases
    ):
        raise ValidationError(
            field="fixtures",
            code="incomplete_fixture_coverage",
            message="Synthetic fixtures do not cover the required training matrix.",
        )
    return coverage
