import json


def test_demo_ingest_populates_home_and_workspace(client):
    response = client.post("/demo/ingest", follow_redirects=True)
    assert response.status_code == 200
    assert "Workflow Inbox" in response.text
    home = client.get("/")
    assert home.status_code == 200
    # Card title is derived from the AI summary, not a hardcoded demo string.
    assert "syncs Shopify orders into Airtable" in home.text
    assert "Review JSON payload" in home.text



def test_workspace_allows_payload_editing_and_shows_audit(client):
    client.post("/demo/ingest", follow_redirects=True)
    pending = client.get("/api/actions/pending").json()
    action_id = pending[0]["id"]
    edited_payload = {"reply": "Operator-approved response", "summary": "edited in test", "category": "sales_inquiry"}
    response = client.post(f"/actions/{action_id}/edit", data={"payload": json.dumps(edited_payload)})
    assert response.status_code == 200
    assert "Operator-approved response" in response.text
    audit = client.get("/audit")
    assert audit.status_code == 200
    assert "Action edited" in audit.text
