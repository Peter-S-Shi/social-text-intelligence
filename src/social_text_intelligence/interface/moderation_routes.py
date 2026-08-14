"""Flask routes for the bounded synthetic moderation training workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue

from ..contracts import (
    AmbiguityLevel,
    CaseDifficulty,
    CaseOrderMode,
    EscalationReason,
    FeedbackTiming,
    LearningObjective,
    MockModerationRecommendation,
    ModerationDisposition,
    ModerationJudgment,
    ModerationPolicy,
    ModerationSeverity,
    ModerationTrainingCase,
    ReferenceDecision,
    ReferenceProvenance,
    TrainingMode,
    UnclearReason,
    ValidationError,
    ViolationCategory,
)
from ..services import (
    CaseFilter,
    ModerationLimits,
    ModerationWorkspace,
    cancel_session,
    clear_prepared_cases,
    compare_attempt,
    export_moderation_session_csv,
    feedback_available,
    filter_training_cases,
    mark_feedback_viewed,
    parse_moderation_judgment,
    parse_trainee_decision,
    prepare_workspace_case,
    restart_session,
    revise_final_decision,
    start_training_session,
    submit_first_decision,
    summarize_training_session,
)
from ..services.moderation_resources import (
    EXPECTED_MOCK_PROVIDER_ID,
    EXPECTED_MOCK_PROVIDER_VERSION,
)
from .batch_state import BatchWorkspace, EphemeralBatchStore
from .moderation_state import EphemeralModerationStore

moderation = Blueprint("moderation", __name__, url_prefix="/moderation")


def _moderation_store() -> EphemeralModerationStore:
    return current_app.extensions["sti_moderation_store"]  # type: ignore[no-any-return]


def _batch_store() -> EphemeralBatchStore:
    return current_app.extensions["sti_batch_store"]  # type: ignore[no-any-return]


def _policy() -> ModerationPolicy:
    return current_app.extensions["sti_moderation_policy"]  # type: ignore[no-any-return]


def _built_in_cases() -> tuple[ModerationTrainingCase, ...]:
    return current_app.extensions["sti_moderation_cases"]  # type: ignore[no-any-return]


def _limits() -> ModerationLimits:
    return current_app.extensions["sti_moderation_limits"]  # type: ignore[no-any-return]


def _form_value(name: str) -> str:
    return request.form.get(name, "").strip()


def _optional_enum(enum_type: type[Any], value: str, *, field: str) -> Any:
    if not value:
        return None
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValidationError(
            field=field,
            code="invalid_choice",
            message=f"Select a supported {field}.",
        ) from error


def _judgment_from_form(prefix: str = "") -> Any:
    return parse_moderation_judgment(
        disposition=_form_value(f"{prefix}disposition"),
        primary_violation=_form_value(f"{prefix}primary_violation"),
        secondary_violations=request.form.getlist(
            f"{prefix}secondary_violations"
        ),
        severity=_form_value(f"{prefix}severity"),
        escalate=_form_value(f"{prefix}escalate") == "true",
        escalation_reason=_form_value(f"{prefix}escalation_reason"),
        unclear_reasons=request.form.getlist(f"{prefix}unclear_reasons"),
    )


def _trainee_from_form() -> Any:
    return parse_trainee_decision(
        disposition=_form_value("disposition"),
        primary_violation=_form_value("primary_violation"),
        secondary_violations=request.form.getlist("secondary_violations"),
        severity=_form_value("severity"),
        escalate=_form_value("escalate") == "true",
        escalation_reason=_form_value("escalation_reason"),
        unclear_reasons=request.form.getlist("unclear_reasons"),
        reasoning=_form_value("reasoning"),
        reviewer_note=_form_value("reviewer_note"),
    )


def _enum_context() -> Mapping[str, Sequence[Any]]:
    return {
        "dispositions": tuple(ModerationDisposition),
        "violation_categories": tuple(ViolationCategory),
        "severities": tuple(ModerationSeverity),
        "escalation_reasons": tuple(EscalationReason),
        "unclear_reasons": tuple(UnclearReason),
        "difficulties": tuple(CaseDifficulty),
        "ambiguity_levels": tuple(AmbiguityLevel),
        "learning_objectives": tuple(LearningObjective),
        "training_modes": tuple(TrainingMode),
        "feedback_timings": tuple(FeedbackTiming),
        "order_modes": tuple(CaseOrderMode),
    }


def _workspace_or_none(token: str) -> ModerationWorkspace | None:
    return _moderation_store().get(token)


def _source_batch(
    workspace: ModerationWorkspace,
) -> BatchWorkspace | None:
    if workspace.source_batch_token is None:
        return None
    return _batch_store().get(workspace.source_batch_token)


def _all_cases(
    workspace: ModerationWorkspace,
) -> tuple[ModerationTrainingCase, ...]:
    return (*_built_in_cases(), *workspace.prepared_cases)


def _render_home(
    *, error_message: str | None = None, status: int = 200
) -> ResponseReturnValue:
    return (
        render_template(
            "moderation_home.html",
            error_message=error_message,
            source_batch_token=request.args.get("batch_token", ""),
            limits=_limits(),
            ttl_seconds=int(
                current_app.config["MODERATION_WORKSPACE_TTL_SECONDS"]
            ),
        ),
        status,
    )


def _render_prepare(
    token: str,
    workspace: ModerationWorkspace,
    *,
    error_message: str | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    source = _source_batch(workspace)
    successful_records = (
        tuple(
            item.report.record
            for item in source.result.outcomes
            if item.report is not None
        )
        if source is not None and source.result is not None
        else ()
    )
    filters = CaseFilter(
        category=_optional_enum(
            ViolationCategory,
            request.args.get("category", ""),
            field="category",
        ),
        difficulty=_optional_enum(
            CaseDifficulty,
            request.args.get("difficulty", ""),
            field="difficulty",
        ),
        ambiguity=_optional_enum(
            AmbiguityLevel,
            request.args.get("ambiguity", ""),
            field="ambiguity",
        ),
        learning_objective=_optional_enum(
            LearningObjective,
            request.args.get("learning_objective", ""),
            field="learning_objective",
        ),
        safety_sensitive=(
            request.args.get("safety_sensitive") == "true"
            if request.args.get("safety_sensitive") in {"true", "false"}
            else None
        ),
    )
    policy = _policy()
    return (
        render_template(
            "moderation_prepare.html",
            token=token,
            workspace=workspace,
            source_batch=source,
            successful_records=successful_records,
            filters=filters,
            built_in_cases=filter_training_cases(
                _built_in_cases(), filters
            ),
            policy=policy,
            policy_clause_ids=tuple(
                clause.clause_id
                for category in policy.categories
                for clause in category.clauses
            ),
            limits=_limits(),
            error_message=error_message,
            **_enum_context(),
        ),
        status,
    )


def _render_session(
    token: str,
    workspace: ModerationWorkspace,
    session_id: str,
    *,
    case_id: str = "",
    error_message: str | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    session = workspace.session(session_id)
    if session is None:
        return Response("Training session not found.", status=404)
    attempts = {item.case_id: item for item in session.attempts}
    frozen = next(
        (
            item
            for item in session.cases
            if item.case.case_id == case_id
        ),
        None,
    )
    if frozen is None:
        frozen = next(
            (
                item
                for item in session.cases
                if item.case.case_id not in attempts
            ),
            session.cases[0],
        )
    selected_case_id = frozen.case.case_id
    attempt = attempts.get(selected_case_id)
    next_unsubmitted = next(
        (
            item.case.case_id
            for item in session.cases
            if item.case.case_id not in attempts
        ),
        None,
    )
    can_view = (
        feedback_available(session, selected_case_id)
        if attempt is not None
        else False
    )
    comparison = (
        compare_attempt(frozen, attempt)
        if attempt is not None and attempt.feedback_viewed
        else None
    )
    return (
        render_template(
            "moderation_session.html",
            token=token,
            workspace=workspace,
            session=session,
            frozen=frozen,
            attempt=attempt,
            can_view_feedback=can_view,
            comparison=comparison,
            submitted_ids=frozenset(attempts),
            next_unsubmitted=next_unsubmitted,
            error_message=error_message,
            **_enum_context(),
        ),
        status,
    )


@moderation.get("")
def home() -> ResponseReturnValue:
    return _render_home()


@moderation.post("/start")
def create_workspace() -> ResponseReturnValue:
    source_batch_token = _form_value("batch_token") or None
    if source_batch_token is not None and _batch_store().get(
        source_batch_token
    ) is None:
        return _render_home(
            error_message="The selected temporary batch expired or was cleared.",
            status=404,
        )
    try:
        token = _moderation_store().create(
            ModerationWorkspace(source_batch_token=source_batch_token)
        )
    except RuntimeError as error:
        return _render_home(error_message=str(error), status=409)
    return redirect(url_for("moderation.prepare", token=token))


@moderation.get("/<token>/prepare")
def prepare(token: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return _render_home(
            error_message="This moderation workspace expired or was cleared.",
            status=404,
        )
    try:
        return _render_prepare(token, workspace)
    except ValidationError as error:
        return _render_prepare(
            token, workspace, error_message=error.message, status=400
        )


@moderation.post("/<token>/prepare")
def prepare_case(token: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    source = _source_batch(workspace)
    if (
        source is None
        or source.result is None
        or source.reviews is None
        or source.insights is None
    ):
        return _render_prepare(
            token,
            workspace,
            error_message=(
                "A completed batch with review and insight state is required "
                "to snapshot a workspace record."
            ),
            status=400,
        )
    source_result = source.result
    source_reviews = source.reviews
    source_insights = source.insights
    try:
        reference = None
        if _form_value("include_reference") == "true":
            alternatives: tuple[ModerationJudgment, ...] = ()
            if _form_value("include_alternative") == "true":
                alternatives = (_judgment_from_form("alternative_"),)
            reference = ReferenceDecision(
                preferred=_judgment_from_form("reference_"),
                acceptable_alternatives=alternatives,
                rationale=_form_value("reference_rationale"),
                policy_clause_ids=tuple(
                    request.form.getlist("policy_clause_ids")
                ),
                provenance=ReferenceProvenance.SELF_AUTHORED,
            )
        mock = None
        if _form_value("include_mock") == "true":
            mock = MockModerationRecommendation(
                judgment=_judgment_from_form("mock_"),
                rationale=_form_value("mock_rationale"),
                provider_id=EXPECTED_MOCK_PROVIDER_ID,
                provider_version=EXPECTED_MOCK_PROVIDER_VERSION,
            )
        policy = _policy()
        updated = _moderation_store().mutate(
            token,
            lambda current: prepare_workspace_case(
                current,
                source_result,
                source_reviews,
                source_insights,
                record_id=_form_value("record_id"),
                excerpt=_form_value("excerpt"),
                difficulty=CaseDifficulty(_form_value("difficulty")),
                learning_objective=LearningObjective(
                    _form_value("learning_objective")
                ),
                reference=reference,
                mock_recommendation=mock,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                valid_policy_clause_ids=tuple(
                    clause.clause_id
                    for category in policy.categories
                    for clause in category.clauses
                ),
                limits=_limits(),
            ),
        )
    except (ValidationError, ValueError) as error:
        message = (
            error.message
            if isinstance(error, ValidationError)
            else "Select supported case preparation values."
        )
        return _render_prepare(
            token, workspace, error_message=message, status=400
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    return redirect(url_for("moderation.prepare", token=token))


@moderation.post("/<token>/prepared/clear")
def clear_cases(token: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        updated = _moderation_store().mutate(token, clear_prepared_cases)
    except ValidationError as error:
        return _render_prepare(
            token, workspace, error_message=error.message, status=409
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    return redirect(url_for("moderation.prepare", token=token))


@moderation.post("/<token>/sessions")
def create_session(token: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        filters = CaseFilter(
            category=_optional_enum(
                ViolationCategory,
                _form_value("category"),
                field="category",
            ),
            difficulty=_optional_enum(
                CaseDifficulty,
                _form_value("difficulty_filter"),
                field="difficulty",
            ),
            ambiguity=_optional_enum(
                AmbiguityLevel,
                _form_value("ambiguity"),
                field="ambiguity",
            ),
            learning_objective=_optional_enum(
                LearningObjective,
                _form_value("learning_objective_filter"),
                field="learning_objective",
            ),
            safety_sensitive=(
                _form_value("safety_sensitive") == "true"
                if _form_value("safety_sensitive") in {"true", "false"}
                else None
            ),
        )
        updated = _moderation_store().mutate(
            token,
            lambda current: start_training_session(
                current,
                filter_training_cases(_all_cases(current), filters),
                case_ids=request.form.getlist("case_ids"),
                case_count=int(_form_value("case_count") or "0"),
                mode=TrainingMode(_form_value("mode")),
                feedback_timing=FeedbackTiming(_form_value("feedback_timing")),
                order_mode=CaseOrderMode(_form_value("order_mode")),
                content_notice_confirmed=(
                    _form_value("content_notice_confirmed") == "true"
                ),
                limits=_limits(),
            ),
        )
    except (ValidationError, ValueError) as error:
        message = (
            error.message
            if isinstance(error, ValidationError)
            else "Select supported session settings and a valid case count."
        )
        return _render_prepare(
            token, workspace, error_message=message, status=400
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    assert updated.active_session_id is not None
    return redirect(
        url_for(
            "moderation.session",
            token=token,
            session_id=updated.active_session_id,
        )
    )


@moderation.get("/<token>/sessions/<session_id>")
def session(token: str, session_id: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    return _render_session(
        token,
        workspace,
        session_id,
        case_id=request.args.get("case_id", ""),
    )


@moderation.post("/<token>/sessions/<session_id>/cases/<case_id>")
def submit_case(
    token: str, session_id: str, case_id: str
) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        decision = _trainee_from_form()
        if _form_value("action") == "revise":
            updated = _moderation_store().mutate(
                token,
                lambda current: revise_final_decision(
                    current,
                    session_id=session_id,
                    case_id=case_id,
                    decision=decision,
                ),
            )
        else:
            updated = _moderation_store().mutate(
                token,
                lambda current: submit_first_decision(
                    current,
                    session_id=session_id,
                    case_id=case_id,
                    decision=decision,
                ),
            )
    except ValidationError as error:
        current = _workspace_or_none(token)
        if current is None:
            return Response("Moderation workspace not found.", status=404)
        return _render_session(
            token,
            current,
            session_id,
            case_id=case_id,
            error_message=error.message,
            status=(
                409
                if error.code
                in {"duplicate_submission", "missing_active_session"}
                else 400
            ),
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    updated_session = updated.session(session_id)
    assert updated_session is not None
    if updated_session.status.value != "active":
        return redirect(
            url_for(
                "moderation.results",
                token=token,
                session_id=session_id,
            )
        )
    return redirect(
        url_for(
            "moderation.session",
            token=token,
            session_id=session_id,
            case_id=case_id,
        )
    )


@moderation.post(
    "/<token>/sessions/<session_id>/cases/<case_id>/feedback"
)
def reveal_feedback(
    token: str, session_id: str, case_id: str
) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        updated = _moderation_store().mutate(
            token,
            lambda current: mark_feedback_viewed(
                current, session_id=session_id, case_id=case_id
            ),
        )
    except ValidationError as error:
        return _render_session(
            token,
            workspace,
            session_id,
            case_id=case_id,
            error_message=error.message,
            status=400,
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    return redirect(
        url_for(
            "moderation.session",
            token=token,
            session_id=session_id,
            case_id=case_id,
        )
    )


@moderation.post("/<token>/sessions/<session_id>/cancel")
def cancel(token: str, session_id: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        updated = _moderation_store().mutate(
            token,
            lambda current: cancel_session(current, session_id=session_id),
        )
    except ValidationError as error:
        return _render_session(
            token,
            workspace,
            session_id,
            error_message=error.message,
            status=409,
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    return redirect(
        url_for(
            "moderation.results", token=token, session_id=session_id
        )
    )


@moderation.post("/<token>/sessions/<session_id>/restart")
def restart(token: str, session_id: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    try:
        updated = _moderation_store().mutate(
            token,
            lambda current: restart_session(
                current, session_id=session_id, limits=_limits()
            ),
        )
    except ValidationError as error:
        return _render_results(
            token,
            workspace,
            session_id,
            error_message=error.message,
            status=409,
        )
    if updated is None:
        return Response("Moderation workspace not found.", status=404)
    assert updated.active_session_id is not None
    return redirect(
        url_for(
            "moderation.session",
            token=token,
            session_id=updated.active_session_id,
        )
    )


def _render_results(
    token: str,
    workspace: ModerationWorkspace,
    session_id: str,
    *,
    error_message: str | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    session_value = workspace.session(session_id)
    if session_value is None:
        return Response("Training session not found.", status=404)
    attempts = {item.case_id: item for item in session_value.attempts}
    rows = tuple(
        (
            frozen,
            attempts.get(frozen.case.case_id),
            (
                compare_attempt(
                    frozen, attempts[frozen.case.case_id]
                )
                if frozen.case.case_id in attempts
                and attempts[frozen.case.case_id].feedback_viewed
                else None
            ),
        )
        for frozen in session_value.cases
    )
    return (
        render_template(
            "moderation_results.html",
            token=token,
            workspace=workspace,
            session=session_value,
            summary=summarize_training_session(session_value),
            rows=rows,
            limits=_limits(),
            error_message=error_message,
        ),
        status,
    )


@moderation.get("/<token>/sessions/<session_id>/results")
def results(token: str, session_id: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    return _render_results(token, workspace, session_id)


@moderation.get("/<token>/sessions/<session_id>/export.csv")
def export_session(token: str, session_id: str) -> ResponseReturnValue:
    workspace = _workspace_or_none(token)
    if workspace is None:
        return Response("Moderation workspace not found.", status=404)
    session_value = workspace.session(session_id)
    if session_value is None:
        return Response("Training session not found.", status=404)
    try:
        content = export_moderation_session_csv(
            session_value,
            include_user_source_text=request.args.get("source_text") == "1",
            include_signals=request.args.get("signals") == "1",
            include_context_notes=request.args.get("context") == "1",
            include_trusted_metadata=request.args.get("metadata") == "1",
        )
    except ValidationError as error:
        return Response(error.message, status=400)
    response = Response(content, mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        "attachment; filename=sti-moderation-training.csv"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@moderation.post("/<token>/clear")
def clear_workspace(token: str) -> ResponseReturnValue:
    _moderation_store().delete(token)
    return redirect(url_for("moderation.home"))
