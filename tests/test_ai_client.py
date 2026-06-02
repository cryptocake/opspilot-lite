from app.ai.fake_client import FakeLLMClient


def classify(text):
    return FakeLLMClient().complete_json("", text)["category"]


def test_fake_client_classifies_sales_inquiry():
    assert classify("Sync Shopify to Airtable and Slack") == "sales_inquiry"


def test_fake_client_classifies_support_request():
    assert classify("API key error, sync stopped working") == "support_request"


def test_fake_client_classifies_meeting_followup():
    assert classify("Meeting notes: Sara owns API docs") == "meeting_followup"
