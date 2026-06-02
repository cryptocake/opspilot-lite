import pytest

from app.approvals.service import approve_action
from app.errors import InvalidStateError
from app.execution.executor import execute_action
from app.models import ActionStatus, ProposedAction, RequestItem, RequestStatus, TriageResult
from app.request_state import recalculate_request_status


class BrokenExecutor:
    def execute(self, action):
        raise RuntimeError("downstream rejected payload")


def make_action(session, source_ref="1"):
    req = RequestItem(source_type="test", source_ref=source_ref, body="x")
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
    return action



def test_executor_requires_approval(session):
    action = make_action(session)
    with pytest.raises(InvalidStateError):
        execute_action(session, action.id)
    approve_action(session, action.id)
    result = execute_action(session, action.id)
    assert result.success is True
    assert session.get(ProposedAction, action.id).status == ActionStatus.EXECUTED.value



def test_failed_execution_marks_action_and_request_failed(session):
    action = make_action(session, source_ref="2")
    approve_action(session, action.id)
    with pytest.raises(RuntimeError):
        execute_action(session, action.id, executor=BrokenExecutor())
    assert session.get(ProposedAction, action.id).status == ActionStatus.FAILED.value
    request_item = session.get(RequestItem, action.request_id)
    assert request_item.status == RequestStatus.FAILED.value
