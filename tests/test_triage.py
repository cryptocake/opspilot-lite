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
    assert output.needs_human_review is True


def test_triage_output_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({"category": "unknown", "priority": "low", "confidence": 2, "summary": "x"})
