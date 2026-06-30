import pytest
from pydantic import ValidationError

from app.ai.fake_client import FakeLLMClient
from app.ai.triage import triage_request
from app.models import RequestItem
from app.schemas import TriageOutput


def test_triage_request_returns_valid_structured_output():
    item = RequestItem(source_type="test", source_ref="1", body="We need Shopify to Airtable automation")
    output = triage_request(FakeLLMClient(), item)
    assert output.category == "sales_inquiry"
    # A confident classification should not demand manual review.
    assert output.needs_human_review is False
    assert output.confidence >= 0.6


def test_triage_escalates_when_uncertain():
    item = RequestItem(source_type="test", source_ref="2", body="hey, can you take a look at this when you get a sec")
    output = triage_request(FakeLLMClient(), item)
    assert output.category == "unknown"
    assert output.needs_human_review is True
    assert output.confidence < 0.6


def test_triage_output_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({"category": "unknown", "priority": "low", "confidence": 2, "summary": "x"})
