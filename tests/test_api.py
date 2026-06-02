from sqlmodel import select

from app.approvals.service import approve_action
from app.execution.executor import execute_action
from app.models import RequestItem


def test_webhook_request_creates_actions(client):
    response = client.post(
        "/api/webhook/request",
        json={"body": "Sync Shopify to Airtable", "subject": "Automation", "source_ref": "hook-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"]
    assert data["duplicate"] is False
    assert len(data["actions"]) == 2



def test_webhook_request_deduplicates_by_source_ref(client, session):
    payload = {"body": "API key error", "subject": "Support", "source_ref": "hook-2"}
    first = client.post("/api/webhook/request", json=payload)
    second = client.post("/api/webhook/request", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(session.exec(select(RequestItem)).all()) == 1



def test_request_listing(client):
    client.post("/api/webhook/request", json={"body": "API key error", "subject": "Support", "source_ref": "hook-3"})
    response = client.get("/api/requests")
    assert response.status_code == 200
    assert len(response.json()) == 1



def test_invalid_transition_returns_conflict(client, session):
    response = client.post(
        "/api/webhook/request",
        json={"body": "Sync Shopify to Airtable", "subject": "Automation", "source_ref": "hook-4"},
    )
    action_id = response.json()["actions"][0]
    approve_action(session, action_id)
    execute_action(session, action_id)
    rejected = client.post(f"/api/actions/{action_id}/reject", json={"reason": "too late"})
    assert rejected.status_code == 409
