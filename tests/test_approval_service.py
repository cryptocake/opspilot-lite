import json

import pytest

from app.approvals.service import approve_action, edit_action, reject_action
from app.errors import InvalidStateError
from app.models import ActionStatus, ProposedAction, RequestItem, RequestStatus, TriageResult
from app.request_state import recalculate_request_status


def make_action(session):
    req = RequestItem(source_type="test", source_ref="1", body="x")
    session.add(req)
    session.flush()
    triage = TriageResult(request_id=req.id, category="unknown", priority="low", confidence=0.5, summary="x")
    session.add(triage)
    session.flush()
    action = ProposedAction(
        request_id=req.id,
        triage_id=triage.id,
        action_type="draft_reply",
        title="Draft",
        payload_json="{}",
    )
    session.add(action)
    session.flush()
    recalculate_request_status(session, req.id)
    session.commit()
    session.refresh(action)
    session.refresh(req)
    return action, req


def test_approve_edit_reject_updates_status_and_payload(session):
    action, request_item = make_action(session)
    assert approve_action(session, action.id).status == ActionStatus.APPROVED.value
    edited = edit_action(session, action.id, {"reply": "new"})
    assert edited.status == ActionStatus.EDITED.value
    assert json.loads(edited.payload_json) == {"reply": "new"}
    rejected = reject_action(session, action.id, "no")
    assert rejected.status == ActionStatus.REJECTED.value
    assert session.get(RequestItem, request_item.id).status == RequestStatus.REJECTED.value


def test_rejected_action_cannot_be_reapproved(session):
    action, _ = make_action(session)
    reject_action(session, action.id, "done")
    with pytest.raises(InvalidStateError):
        approve_action(session, action.id)
