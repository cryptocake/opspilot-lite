from app.request_state import CONFIDENCE_REVIEW_THRESHOLD, triage_needs_review


def test_triage_needs_review_policy():
    assert triage_needs_review(0.95, needs_human_review=False) is False
    assert triage_needs_review(0.95, needs_human_review=True) is True
    assert triage_needs_review(CONFIDENCE_REVIEW_THRESHOLD - 0.01, needs_human_review=False) is True
    assert triage_needs_review(CONFIDENCE_REVIEW_THRESHOLD, needs_human_review=False) is False


def test_low_confidence_request_cannot_be_bulk_approved(client):
    created = client.post(
        "/api/webhook/request",
        json={"body": "just checking in, nothing specific", "source_ref": "review-1"},
    ).json()
    request_id = created["request_id"]
    action_id = created["actions"][0]

    bulk = client.post(f"/requests/{request_id}/approve-actions")
    assert bulk.status_code == 409

    # Individual approval is still allowed — review happens action by action.
    single = client.post(f"/actions/{action_id}/approve")
    assert single.status_code == 200


def test_confident_request_can_be_bulk_approved(client):
    created = client.post(
        "/api/webhook/request",
        json={"body": "Sync Shopify orders into Airtable", "source_ref": "review-2"},
    ).json()
    request_id = created["request_id"]

    bulk = client.post(f"/requests/{request_id}/approve-actions")
    assert bulk.status_code == 200
