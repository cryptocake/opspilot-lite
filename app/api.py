from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, desc, select

from app.ai.factory import get_llm_client
from app.approvals.service import approve_action, edit_action, reject_action
from app.config import get_settings
from app.db import get_session
from app.errors import ConfigurationError, InvalidStateError, NotFoundError
from app.execution.executor import execute_action
from app.ingestion.folder import ingest_folder
from app.ingestion.webhook import ingest_webhook_request
from app.models import AuditEvent, ProposedAction, RequestItem, TriageResult
from app.request_state import OPEN_ACTION_STATUSES
from app.schemas import WebhookRequest
from app.service import process_all_new_requests, process_new_request

router = APIRouter(prefix="/api")


class EditPayload(BaseModel):
    payload: dict


class RejectPayload(BaseModel):
    reason: str = ""


@router.post("/ingest/folder")
def api_ingest_folder(path: str | None = None, session: Session = Depends(get_session)):
    folder = path or get_settings().inbox_path
    items = ingest_folder(session, folder)
    return {"ingested": len(items), "request_ids": [item.id for item in items]}


@router.post("/process")
def api_process(session: Session = Depends(get_session)):
    processed = process_all_new_requests(session, get_llm_client())
    return {"processed": len(processed), "actions": sum(len(actions) for _, actions in processed)}


@router.post("/webhook/request")
def api_webhook_request(payload: WebhookRequest, session: Session = Depends(get_session)):
    try:
        item, created = ingest_webhook_request(session, payload)
        actions = process_new_request(session, item, get_llm_client())
        if not actions:
            actions = _request_actions(session, item.id or 0)
        return {"request_id": item.id, "actions": [action.id for action in actions], "duplicate": not created}
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)


@router.get("/requests")
def api_requests(session: Session = Depends(get_session)):
    return session.exec(select(RequestItem).order_by(desc(RequestItem.created_at))).all()


@router.get("/requests/{request_id}")
def api_request_detail(request_id: int, session: Session = Depends(get_session)):
    item = session.get(RequestItem, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
    triage = session.exec(select(TriageResult).where(TriageResult.request_id == request_id)).first()
    return {"request": item, "triage": triage, "actions": _request_actions(session, request_id)}


@router.get("/actions/pending")
def api_pending_actions(session: Session = Depends(get_session)):
    return session.exec(select(ProposedAction).where(ProposedAction.status.in_(tuple(OPEN_ACTION_STATUSES)))).all()


@router.post("/actions/{action_id}/approve")
def api_approve(action_id: int, session: Session = Depends(get_session)):
    try:
        return approve_action(session, action_id)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)


@router.post("/actions/{action_id}/reject")
def api_reject(action_id: int, payload: RejectPayload | None = None, session: Session = Depends(get_session)):
    try:
        return reject_action(session, action_id, payload.reason if payload else "")
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)


@router.post("/actions/{action_id}/edit")
def api_edit(action_id: int, payload: EditPayload, session: Session = Depends(get_session)):
    try:
        return edit_action(session, action_id, payload.payload)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)


@router.post("/actions/{action_id}/execute")
def api_execute(action_id: int, session: Session = Depends(get_session)):
    try:
        result = execute_action(session, action_id)
    except (ConfigurationError, InvalidStateError, NotFoundError) as exc:
        _raise_http_error(exc)
    return {"success": result.success, "message": result.message, "output": result.output}


@router.get("/audit")
def api_audit(session: Session = Depends(get_session)):
    return session.exec(select(AuditEvent).order_by(desc(AuditEvent.created_at))).all()


def _request_actions(session: Session, request_id: int) -> list[ProposedAction]:
    statement = (
        select(ProposedAction)
        .where(ProposedAction.request_id == request_id)
        .order_by(ProposedAction.created_at)
    )
    return session.exec(statement).all()


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidStateError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, ConfigurationError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    raise exc
