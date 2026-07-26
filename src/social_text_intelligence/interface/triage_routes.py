"""Flask routes for the local Support Triage workbench."""

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
    IssueCategory,
    MockProvenance,
    MockTriageSuggestion,
    NextAction,
    RecommendedQueue,
    SupportIntent,
    SupportTicket,
    TicketComplexity,
    TicketSource,
    TicketStatus,
    TriageEscalationReason,
    TriageFields,
    TriageGuide,
    TriageMode,
    TriageUrgency,
    ValidationError,
    validate_final_fields,
)
from ..services import (
    TriageFilter,
    TriageLimits,
    TriageWorkspace,
    add_synthetic_tickets,
    compare_to_mock,
    export_triage_csv,
    filter_triage_entries,
    finalize_ticket,
    mock_is_visible,
    new_triage_workspace,
    parse_triage_fields,
    prepare_workspace_ticket,
    reveal_ticket_mock,
    revise_ticket,
    save_triage_draft,
    summarize_triage,
)
from .batch_state import BatchWorkspace, EphemeralBatchStore
from .triage_state import EphemeralTriageStore

triage = Blueprint("triage", __name__, url_prefix="/triage")


def _store() -> EphemeralTriageStore:
    return current_app.extensions["sti_triage_store"]  # type: ignore[no-any-return]


def _batch_store() -> EphemeralBatchStore:
    return current_app.extensions["sti_batch_store"]  # type: ignore[no-any-return]


def _guide() -> TriageGuide:
    return current_app.extensions["sti_triage_guide"]  # type: ignore[no-any-return]


def _tickets() -> tuple[SupportTicket, ...]:
    return current_app.extensions["sti_support_tickets"]  # type: ignore[no-any-return]


def _limits() -> TriageLimits:
    return current_app.extensions["sti_triage_limits"]  # type: ignore[no-any-return]


def _enum_context() -> Mapping[str, Sequence[Any]]:
    return {
        "intents": tuple(SupportIntent),
        "categories": tuple(IssueCategory),
        "urgencies": tuple(TriageUrgency),
        "queues": tuple(RecommendedQueue),
        "escalation_reasons": tuple(TriageEscalationReason),
        "next_actions": tuple(NextAction),
        "complexities": tuple(TicketComplexity),
        "modes": tuple(TriageMode),
        "statuses": tuple(TicketStatus),
        "sources": tuple(TicketSource),
    }


def _form_value(name: str) -> str:
    return request.form.get(name, "").strip()


def _fields_from_request(prefix: str = "") -> TriageFields:
    return parse_triage_fields(
        primary_intent=_form_value(f"{prefix}primary_intent"),
        secondary_intents=request.form.getlist(f"{prefix}secondary_intents"),
        issue_category=_form_value(f"{prefix}issue_category"),
        urgency=_form_value(f"{prefix}urgency"),
        recommended_queue=_form_value(f"{prefix}recommended_queue"),
        escalation_required=_form_value(f"{prefix}escalation_required")
        == "true",
        escalation_reason=_form_value(f"{prefix}escalation_reason"),
        primary_next_action=_form_value(f"{prefix}primary_next_action"),
        secondary_next_actions=request.form.getlist(
            f"{prefix}secondary_next_actions"
        ),
        unclear_reason=_form_value(f"{prefix}unclear_reason"),
        human_notes=_form_value(f"{prefix}human_notes"),
    )


def _optional_enum(enum_type: type[Any], value: str) -> Any:
    if not value:
        return None
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValidationError(
            field="filter",
            code="invalid_filter",
            message="A filter contains an unsupported value.",
        ) from error


def _workspace(token: str) -> TriageWorkspace | None:
    return _store().get(token)


def _source_batch(workspace: TriageWorkspace) -> BatchWorkspace | None:
    if workspace.source_batch_token is None:
        return None
    return _batch_store().get(workspace.source_batch_token)


def _render_home(
    *, error_message: str | None = None, status: int = 200
) -> ResponseReturnValue:
    return (
        render_template(
            "triage_home.html",
            error_message=error_message,
            source_batch_token=request.args.get("batch_token", ""),
            limits=_limits(),
            ttl_seconds=int(current_app.config["TRIAGE_WORKSPACE_TTL_SECONDS"]),
            **_enum_context(),
        ),
        status,
    )


def _render_guide(
    token: str,
    workspace: TriageWorkspace,
    *,
    error_message: str | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    source = _source_batch(workspace)
    eligible = (
        tuple(
            outcome
            for outcome in source.result.outcomes
            if outcome.prepared.record is not None
        )
        if source is not None and source.result is not None
        else ()
    )
    complexity = request.args.get("complexity", "")
    mock_filter = request.args.get("mock", "")
    built_ins = tuple(
        ticket
        for ticket in _tickets()
        if (not complexity or ticket.complexity.value == complexity)
        and (
            not mock_filter
            or (ticket.mock_suggestion is not None)
            is (mock_filter == "available")
        )
    )
    return (
        render_template(
            "triage_guide.html",
            token=token,
            workspace=workspace,
            guide=_guide(),
            built_in_tickets=built_ins,
            source_batch=source,
            eligible_records=eligible,
            error_message=error_message,
            limits=_limits(),
            blank_mock_fields=TriageFields(),
            complexity_filter=complexity,
            mock_filter=mock_filter,
            **_enum_context(),
        ),
        status,
    )


def _filters() -> TriageFilter:
    escalation = request.args.get("escalation", "")
    mock = request.args.get("mock", "")
    disagreement = request.args.get("disagreement", "")
    warning = request.args.get("warning", "")
    return TriageFilter(
        status=_optional_enum(TicketStatus, request.args.get("status", "")),
        source=_optional_enum(TicketSource, request.args.get("source", "")),
        source_label=request.args.get("source_label", "").strip(),
        topic=request.args.get("topic", "").strip(),
        community=request.args.get("community", "").strip(),
        primary_intent=_optional_enum(
            SupportIntent, request.args.get("primary_intent", "")
        ),
        issue_category=_optional_enum(
            IssueCategory, request.args.get("issue_category", "")
        ),
        urgency=_optional_enum(
            TriageUrgency, request.args.get("urgency", "")
        ),
        recommended_queue=_optional_enum(
            RecommendedQueue, request.args.get("queue", "")
        ),
        escalation_required=(
            escalation == "true" if escalation in {"true", "false"} else None
        ),
        mock_available=(
            mock == "available"
            if mock in {"available", "unavailable"}
            else None
        ),
        disagreement=(
            disagreement == "true"
            if disagreement in {"true", "false"}
            else None
        ),
        guidance_warning=(
            warning == "true" if warning in {"true", "false"} else None
        ),
        text_search=request.args.get("q", "").strip(),
    )


def _render_workspace(
    token: str,
    workspace: TriageWorkspace,
    *,
    error_message: str | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    filters = _filters()
    sort_by = request.args.get("sort", "original")
    return (
        render_template(
            "triage_workspace.html",
            token=token,
            workspace=workspace,
            entries=filter_triage_entries(
                workspace, filters, sort_by=sort_by
            ),
            filters=filters,
            sort_by=sort_by,
            error_message=error_message,
            **_enum_context(),
        ),
        status,
    )


def _render_ticket(
    token: str,
    workspace: TriageWorkspace,
    ticket_id: str,
    *,
    error_message: str | None = None,
    submitted_fields: TriageFields | None = None,
    status: int = 200,
) -> ResponseReturnValue:
    entry = workspace.entry(ticket_id)
    if entry is None:
        return Response("Support triage ticket not found.", status=404)
    visible = mock_is_visible(workspace, entry)
    form_fields = (
        submitted_fields
        or (entry.final.fields if entry.final else None)
        or (entry.draft.fields if entry.draft else None)
        or TriageFields()
    )
    return (
        render_template(
            "triage_ticket.html",
            token=token,
            workspace=workspace,
            entry=entry,
            form_fields=form_fields,
            mock_visible=visible,
            comparison=(
                compare_to_mock(
                    entry.final.fields, entry.ticket.mock_suggestion
                )
                if entry.final is not None and visible
                else None
            ),
            error_message=error_message,
            **_enum_context(),
        ),
        status,
    )


@triage.get("")
def home() -> ResponseReturnValue:
    return _render_home()


@triage.post("/start")
def create_workspace() -> ResponseReturnValue:
    try:
        mode = TriageMode(_form_value("mode"))
        source_batch_token = _form_value("batch_token") or None
        if (
            source_batch_token is not None
            and _batch_store().get(source_batch_token) is None
        ):
            raise ValidationError(
                field="batch_token",
                code="not_found",
                message="The temporary batch token was not found or expired.",
            )
        token = _store().create(
            new_triage_workspace(
                mode=mode, source_batch_token=source_batch_token
            )
        )
    except (ValidationError, ValueError, RuntimeError) as error:
        message = (
            error.message if isinstance(error, ValidationError) else str(error)
        )
        return _render_home(error_message=message, status=400)
    return redirect(url_for("triage.guide", token=token))


@triage.get("/<token>/guide")
def guide(token: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return _render_home(
            error_message="This support triage workspace expired or was cleared.",
            status=404,
        )
    return _render_guide(token, workspace)


@triage.post("/<token>/synthetic")
def add_synthetic(token: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    try:
        updated = add_synthetic_tickets(
            workspace,
            _tickets(),
            ticket_ids=request.form.getlist("ticket_ids"),
            limits=_limits(),
        )
        _store().replace(token, updated)
    except ValidationError as error:
        return _render_guide(
            token, workspace, error_message=error.message, status=400
        )
    return redirect(url_for("triage.workspace", token=token))


@triage.post("/<token>/workspace-ticket")
def add_workspace_ticket(token: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    source = _source_batch(workspace)
    if source is None or source.result is None:
        return _render_guide(
            token,
            workspace,
            error_message="A current analyzed batch workspace is required.",
            status=400,
        )
    try:
        mock = None
        if _form_value("include_self_authored_mock") == "true":
            mock_fields = _fields_from_request("mock_")
            validate_final_fields(mock_fields)
            mock = MockTriageSuggestion(
                fields=mock_fields,
                rationale=_form_value("mock_rationale"),
                provider_id="sti-self-authored-support-triage-mock",
                provider_version="workspace-v1",
                provenance=MockProvenance.SELF_AUTHORED_MOCK,
            )
        updated = prepare_workspace_ticket(
            workspace,
            source.result,
            source.reviews,
            source.insights,
            record_id=_form_value("record_id"),
            excerpt=_form_value("excerpt"),
            complexity=TicketComplexity(_form_value("complexity")),
            guide=_guide(),
            applicable_rule_ids=request.form.getlist("rule_ids"),
            mock_suggestion=mock,
            limits=_limits(),
        )
        _store().replace(token, updated)
    except (ValidationError, ValueError) as error:
        message = (
            error.message if isinstance(error, ValidationError) else str(error)
        )
        return _render_guide(
            token, workspace, error_message=message, status=400
        )
    return redirect(url_for("triage.workspace", token=token))


@triage.get("/<token>/workspace")
def workspace(token: str) -> ResponseReturnValue:
    current = _workspace(token)
    if current is None:
        return Response("Support triage workspace not found.", status=404)
    try:
        return _render_workspace(token, current)
    except ValidationError as error:
        return _render_workspace(
            token, current, error_message=error.message, status=400
        )


@triage.get("/<token>/tickets/<ticket_id>")
def ticket(token: str, ticket_id: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    return _render_ticket(token, workspace, ticket_id)


def _save_action(
    token: str, ticket_id: str, *, action: str
) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    fields: TriageFields | None = None
    try:
        fields = _fields_from_request()
        if action == "draft":
            updated = save_triage_draft(
                workspace, ticket_id=ticket_id, fields=fields
            )
        elif action == "finalize":
            updated = finalize_ticket(
                workspace, ticket_id=ticket_id, fields=fields
            )
        else:
            updated = revise_ticket(
                workspace, ticket_id=ticket_id, fields=fields
            )
        _store().replace(token, updated)
    except ValidationError as error:
        return _render_ticket(
            token,
            workspace,
            ticket_id,
            error_message=error.message,
            submitted_fields=fields,
            status=400,
        )
    return redirect(url_for("triage.ticket", token=token, ticket_id=ticket_id))


@triage.post("/<token>/tickets/<ticket_id>/draft")
def save_draft(token: str, ticket_id: str) -> ResponseReturnValue:
    return _save_action(token, ticket_id, action="draft")


@triage.post("/<token>/tickets/<ticket_id>/finalize")
def finalize(token: str, ticket_id: str) -> ResponseReturnValue:
    return _save_action(token, ticket_id, action="finalize")


@triage.post("/<token>/tickets/<ticket_id>/revise")
def revise(token: str, ticket_id: str) -> ResponseReturnValue:
    return _save_action(token, ticket_id, action="revise")


@triage.post("/<token>/tickets/<ticket_id>/reveal")
def reveal(token: str, ticket_id: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    try:
        updated = reveal_ticket_mock(workspace, ticket_id=ticket_id)
        _store().replace(token, updated)
    except ValidationError as error:
        return _render_ticket(
            token,
            workspace,
            ticket_id,
            error_message=error.message,
            status=400,
        )
    return redirect(url_for("triage.ticket", token=token, ticket_id=ticket_id))


@triage.get("/<token>/summary")
def summary(token: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    return render_template(
        "triage_summary.html",
        token=token,
        workspace=workspace,
        summary=summarize_triage(workspace),
    )


@triage.get("/<token>/export.csv")
def export(token: str) -> ResponseReturnValue:
    workspace = _workspace(token)
    if workspace is None:
        return Response("Support triage workspace not found.", status=404)
    content = export_triage_csv(
        workspace,
        include_source_text=request.args.get("source_text") == "1",
        include_signals=request.args.get("signals") == "1",
        include_human_review=request.args.get("human_review") == "1",
        include_context_notes=request.args.get("context_notes") == "1",
        include_trusted_metadata=request.args.get("metadata") == "1",
    )
    response = Response(content, mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        "attachment; filename=sti-support-triage.csv"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@triage.post("/<token>/clear")
def clear(token: str) -> ResponseReturnValue:
    _store().delete(token)
    return redirect(url_for("triage.home"))
