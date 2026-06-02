import json
from typing import Any

from sqlmodel import Session

from app.models import AuditEvent


def record_event(
    session: Session,
    event_type: str,
    message: str,
    request_id: int | None = None,
    action_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        request_id=request_id,
        action_id=action_id,
        event_type=event_type,
        message=message,
        metadata_json=json.dumps(metadata, sort_keys=True) if metadata is not None else None,
    )
    session.add(event)
    return event
