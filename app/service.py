import json

from sqlmodel import Session, select

from app.ai.client import LLMClient
from app.ai.triage import triage_request
from app.audit import record_event
from app.models import RequestItem, RequestStatus, TriageResult
from app.request_state import recalculate_request_status
from app.workflows.router import route_workflow


def process_new_request(session: Session, request_item: RequestItem, llm_client: LLMClient):
    if request_item.status != RequestStatus.NEW.value:
        return []
    triage = triage_request(llm_client, request_item)
    triage_result = TriageResult(
        request_id=request_item.id,
        category=triage.category,
        priority=triage.priority,
        confidence=triage.confidence,
        summary=triage.summary,
        extracted_json=json.dumps(triage.model_dump(), sort_keys=True),
    )
    session.add(triage_result)
    session.flush()
    record_event(
        session,
        "request.triaged",
        f"Triaged as {triage.category}",
        request_id=request_item.id,
        metadata=triage.model_dump(),
    )
    actions = route_workflow(session, request_item, triage_result, triage)
    recalculate_request_status(session, request_item.id or 0)
    session.commit()
    return actions


def process_all_new_requests(session: Session, llm_client: LLMClient):
    requests = session.exec(select(RequestItem).where(RequestItem.status == RequestStatus.NEW.value)).all()
    processed = []
    for request_item in requests:
        actions = process_new_request(session, request_item, llm_client)
        processed.append((request_item, actions))
    return processed
