import json
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, desc, select

from app.ai.factory import get_llm_client
from app.approvals.service import approve_action, edit_action, reject_action
from app.config import get_settings
from app.db import get_session
from app.errors import ConfigurationError, InvalidStateError, NotFoundError
from app.execution.executor import execute_action
from app.ingestion.folder import ingest_folder
from app.models import AuditEvent, ProposedAction, RequestItem, TriageResult
from app.request_state import COMPLETED_ACTION_STATUSES, OPEN_ACTION_STATUSES
from app.service import process_all_new_requests

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

CATEGORY_LABELS = {
    "sales_inquiry": "Sales inquiry",
    "support_request": "Support request",
    "meeting_followup": "Meeting follow-up",
    "finance_invoice": "Finance / invoice",
    "internal_task": "Internal task",
    "unknown": "Needs review",
}

ACTION_LABELS = {
    "draft_reply": "Prepare customer reply",
    "create_task": "Create internal task",
    "create_discovery_checklist": "Build discovery checklist",
    "summarize_meeting": "Summarize decisions and owners",
}

STATUS_LABELS = {
    "new": "New",
    "triaged": "Triaged",
    "pending_approval": "Waiting for approval",
    "completed": "Completed",
    "rejected": "Rejected",
    "failed": "Failed",
    "pending": "Needs approval",
    "approved": "Approved",
    "edited": "Edited by operator",
    "executed": "Executed",
}

EVENT_LABELS = {
    "request.ingested": "Request received",
    "request.triaged": "AI triage completed",
    "action.proposed": "Action proposed",
    "action.approved": "Action approved",
    "action.edited": "Action edited",
    "action.rejected": "Action rejected",
    "action.executed": "Action executed",
    "action.failed": "Execution failed",
}


def _safe_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}



def _display_text(text: str | None) -> str:
    return " ".join((text or "").split())



def _human_event_message(event: AuditEvent) -> str:
    message = event.message
    replacements = {
        "create_task": "Create task",
        "summarize_meeting": "Summarize meeting",
        "draft_reply": "Draft reply",
        "create_discovery_checklist": "Create discovery checklist",
        "sales_inquiry": "Sales inquiry",
        "support_request": "Support request",
        "meeting_followup": "Meeting follow-up",
        "finance_invoice": "Finance / invoice",
    }
    for raw, label in replacements.items():
        message = message.replace(raw, label)
    message = message.replace("Proposed ", "Proposed: ")
    message = message.replace("Triaged as ", "Classified as ")
    return message



def _payload_highlights(action: ProposedAction) -> list[dict[str, str]]:
    payload = _safe_json(action.payload_json)
    if action.action_type == "draft_reply":
        return [
            {"label": "Suggested reply", "value": _display_text(payload.get("reply"))},
            {"label": "Why", "value": _display_text(payload.get("summary"))},
        ]
    if action.action_type == "create_discovery_checklist":
        systems = payload.get("systems_detected") or []
        questions = payload.get("questions") or []
        return [
            {"label": "Detected systems", "value": ", ".join(systems) if systems else "To confirm"},
            {"label": "Discovery focus", "value": _display_text(" • ".join(questions))},
        ]
    if action.action_type == "create_task":
        return [
            {"label": "Task", "value": _display_text(payload.get("title"))},
            {"label": "Priority", "value": str(payload.get("priority", "medium")).title()},
        ]
    if action.action_type == "summarize_meeting":
        return [
            {"label": "Summary", "value": _display_text(payload.get("summary"))},
            {"label": "Next step", "value": _display_text(payload.get("next_step"))},
        ]
    return [{"label": "Action details", "value": _display_text(str(payload))}]



def _business_impact(action: ProposedAction) -> str:
    impacts = {
        "draft_reply": "Produces a reviewable customer message before anything is sent externally.",
        "create_task": "Turns the request into accountable internal work with context and priority.",
        "create_discovery_checklist": "Creates the questions needed to scope the automation safely.",
        "summarize_meeting": "Extracts decisions, owners, and next steps from unstructured notes.",
    }
    return impacts.get(action.action_type, "Moves the request into a controlled, auditable workflow.")



def _action_view(action: ProposedAction) -> dict[str, Any]:
    payload = _safe_json(action.payload_json)
    return {
        "model": action,
        "label": ACTION_LABELS.get(action.action_type, action.action_type.replace("_", " ").title()),
        "impact": _business_impact(action),
        "status_label": STATUS_LABELS.get(action.status, action.status.title()),
        "status": action.status,
        "editable": action.status in OPEN_ACTION_STATUSES,
        "highlights": [item for item in _payload_highlights(action) if item["value"]],
        "payload": payload,
        "payload_pretty": json.dumps(payload, indent=2, sort_keys=True),
    }



def _friendly_request_title(item: RequestItem, triage: dict[str, Any] | None) -> str:
    body = item.body.lower()
    if "shopify" in body and "airtable" in body:
        return "Shopify → Airtable automation request"
    if "api key" in body or "stopped working" in body:
        return "API key rotation broke nightly sync"
    if "meeting notes" in body or "launch target" in body:
        return "Meeting follow-up with owners and launch date"
    if triage:
        return triage["category_label"]
    return item.subject or "Untitled request"



def _workflow_stage(actions: list[ProposedAction]) -> dict[str, Any]:
    if not actions:
        active = "Understanding"
    else:
        statuses = {action.status for action in actions}
        if "failed" in statuses:
            active = "Failed"
        elif statuses == {"rejected"}:
            active = "Rejected"
        elif statuses <= COMPLETED_ACTION_STATUSES:
            active = "Completed"
        elif {"approved", "edited"} & statuses:
            active = "Ready to execute"
        else:
            active = "Waiting approval"
    steps = [
        {"label": "Received", "state": "done"},
        {"label": "Understood", "state": "done" if actions else "active"},
        {"label": "Actions drafted", "state": "done" if actions else "todo"},
        {
            "label": "Human review",
            "state": "active" if active in {"Waiting approval", "Failed"} else "done" if actions else "todo",
        },
        {
            "label": "Executed",
            "state": "done" if active == "Completed" else "active" if active == "Ready to execute" else "todo",
        },
    ]
    return {"active": active, "steps": steps}



def _request_events(events: list[AuditEvent], request_id: int, limit: int = 4) -> list[dict[str, Any]]:
    matching = [event for event in events if event.request_id == request_id]
    return [_event_view(event) for event in matching[:limit]]



def _workflow_card(
    item: RequestItem,
    triage: dict[str, Any] | None,
    actions: list[ProposedAction],
    events: list[AuditEvent],
) -> dict[str, Any]:
    open_actions = [action for action in actions if action.status in OPEN_ACTION_STATUSES]
    return {
        "item": item,
        "title": _friendly_request_title(item, triage),
        "status_label": STATUS_LABELS.get(item.status, item.status.title()),
        "triage": triage,
        "actions": [_action_view(action) for action in actions],
        "open_action_count": len(open_actions),
        "stage": _workflow_stage(actions),
        "events": _request_events(events, item.id or 0),
    }



def _triage_view(triage: TriageResult | None) -> dict[str, Any] | None:
    if not triage:
        return None
    extracted = _safe_json(triage.extracted_json)
    entities = extracted.get("entities") or []
    return {
        "model": triage,
        "category_label": CATEGORY_LABELS.get(triage.category, triage.category.replace("_", " ").title()),
        "priority": triage.priority.title(),
        "confidence_percent": round(triage.confidence * 100),
        "summary": triage.summary,
        "entities": entities,
    }



def _event_view(event: AuditEvent) -> dict[str, Any]:
    return {
        "model": event,
        "label": EVENT_LABELS.get(event.event_type, event.event_type.replace(".", " ").title()),
        "message": _human_event_message(event),
    }



def _ctx(request: Request, session: Session) -> dict[str, Any]:
    requests = session.exec(select(RequestItem).order_by(desc(RequestItem.created_at))).all()
    actions = session.exec(select(ProposedAction).order_by(ProposedAction.created_at)).all()
    events = session.exec(select(AuditEvent).order_by(desc(AuditEvent.created_at))).all()
    triage_results = session.exec(select(TriageResult)).all()
    triage_by_request = {triage.request_id: _triage_view(triage) for triage in triage_results}
    actions_by_request: dict[int, list[ProposedAction]] = {}
    for action in actions:
        actions_by_request.setdefault(action.request_id, []).append(action)
    workflow_cards = [
        _workflow_card(
            item,
            triage_by_request.get(item.id),
            actions_by_request.get(item.id or 0, []),
            events,
        )
        for item in requests
    ]
    open_actions = [action for action in actions if action.status in OPEN_ACTION_STATUSES]
    completed_actions = [action for action in actions if action.status == "executed"]
    failed_actions = [action for action in actions if action.status == "failed"]
    return {
        "request": request,
        "requests": requests,
        "workflow_cards": workflow_cards,
        "request_count": len(requests),
        "actions": [_action_view(action) for action in actions],
        "pending_actions": [_action_view(action) for action in open_actions],
        "completed_action_count": len(completed_actions),
        "failed_action_count": len(failed_actions),
        "events": [_event_view(event) for event in events[:8]],
        "triage_by_request": triage_by_request,
        "status_labels": STATUS_LABELS,
    }


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "index.html", _ctx(request, session))



def _workspace_response(request: Request, session: Session):
    template = "workspace_content.html" if request.headers.get("HX-Request") else "workspace.html"
    return templates.TemplateResponse(request, template, _ctx(request, session))


@router.get("/workspace", response_class=HTMLResponse)
def workspace(request: Request, session: Session = Depends(get_session)):
    return _workspace_response(request, session)


@router.post("/demo/ingest")
def demo_ingest(session: Session = Depends(get_session)):
    ingest_folder(session, get_settings().inbox_path)
    process_all_new_requests(session, get_llm_client())
    return RedirectResponse(url="/workspace", status_code=303)


@router.get("/requests/{request_id}", response_class=HTMLResponse)
def request_detail(request_id: int, request: Request, session: Session = Depends(get_session)):
    item = session.get(RequestItem, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
    triage = session.exec(select(TriageResult).where(TriageResult.request_id == request_id)).first()
    actions = session.exec(
        select(ProposedAction).where(ProposedAction.request_id == request_id).order_by(ProposedAction.created_at)
    ).all()
    events = session.exec(
        select(AuditEvent).where(AuditEvent.request_id == request_id).order_by(desc(AuditEvent.created_at))
    ).all()
    return templates.TemplateResponse(
        request,
        "request_detail.html",
        {
            "request": request,
            "item": item,
            "triage": _triage_view(triage),
            "actions": [_action_view(action) for action in actions],
            "events": [_event_view(event) for event in events],
            "status_labels": STATUS_LABELS,
        },
    )


@router.get("/audit", response_class=HTMLResponse)
def audit(request: Request, session: Session = Depends(get_session)):
    events = session.exec(select(AuditEvent).order_by(desc(AuditEvent.created_at))).all()
    return templates.TemplateResponse(
        request,
        "audit.html",
        {"request": request, "events": [_event_view(event) for event in events]},
    )


@router.post("/requests/{request_id}/approve-actions")
def web_approve_request_actions(
    request_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    actions = session.exec(
        select(ProposedAction).where(
            ProposedAction.request_id == request_id,
            ProposedAction.status == "pending",
        )
    ).all()
    try:
        for action in actions:
            approve_action(session, action.id or 0)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return _workspace_response(request, session)


@router.post("/actions/{action_id}/approve")
def web_approve(action_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        approve_action(session, action_id)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return _workspace_response(request, session)


@router.post("/actions/{action_id}/reject")
def web_reject(
    action_id: int,
    request: Request,
    reason: str = Form("Rejected by operator"),
    session: Session = Depends(get_session),
):
    try:
        reject_action(session, action_id, reason)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return _workspace_response(request, session)


@router.post("/actions/{action_id}/edit")
def web_edit(
    action_id: int,
    request: Request,
    payload: str = Form(...),
    session: Session = Depends(get_session),
):
    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Payload must be valid JSON") from exc
    if not isinstance(parsed_payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    try:
        edit_action(session, action_id, parsed_payload)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return _workspace_response(request, session)


@router.post("/actions/{action_id}/execute")
def web_execute(action_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        execute_action(session, action_id)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return _workspace_response(request, session)



def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidStateError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ConfigurationError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    raise exc
