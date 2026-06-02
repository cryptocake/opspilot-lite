import json

from sqlmodel import select

from app.audit import record_event
from app.models import AuditEvent


def test_record_event_stores_metadata(session):
    record_event(session, "request.ingested", "hello", request_id=1, metadata={"a": 1})
    session.commit()
    event = session.exec(select(AuditEvent)).one()
    assert event.event_type == "request.ingested"
    assert json.loads(event.metadata_json) == {"a": 1}
