from app.ai.fake_client import FakeLLMClient
from app.approvals.service import approve_action, reject_action
from app.execution.executor import execute_action
from app.models import RequestItem, RequestStatus
from app.service import process_new_request


def test_process_new_request_creates_triage_and_actions(session):
    item = RequestItem(source_type="test", source_ref="1", body="Sync Shopify to Airtable")
    session.add(item)
    session.commit()
    session.refresh(item)
    actions = process_new_request(session, item, FakeLLMClient())
    assert len(actions) == 2
    assert session.get(RequestItem, item.id).status == RequestStatus.PENDING_APPROVAL.value



def test_request_completes_when_actions_are_executed_or_rejected(session):
    item = RequestItem(source_type="test", source_ref="2", body="Sync Shopify to Airtable")
    session.add(item)
    session.commit()
    session.refresh(item)
    actions = process_new_request(session, item, FakeLLMClient())
    approve_action(session, actions[0].id)
    execute_action(session, actions[0].id)
    reject_action(session, actions[1].id, "Not needed")
    assert session.get(RequestItem, item.id).status == RequestStatus.COMPLETED.value
