import json

from app.models import RequestItem, TriageResult
from app.schemas import TriageOutput
from app.workflows.router import route_workflow


def test_sales_inquiry_routes_to_reply_and_checklist(session):
    request = RequestItem(source_type="test", source_ref="1", body="Shopify automation")
    session.add(request)
    session.flush()
    triage_model = TriageResult(
        request_id=request.id, category="sales_inquiry", priority="medium", confidence=0.9, summary="x"
    )
    session.add(triage_model)
    session.flush()
    triage = TriageOutput(category="sales_inquiry", priority="medium", confidence=0.9, summary="x")
    actions = route_workflow(session, request, triage_model, triage)
    assert [a.action_type for a in actions] == ["draft_reply", "create_discovery_checklist"]
    assert json.loads(actions[0].payload_json)["category"] == "sales_inquiry"
