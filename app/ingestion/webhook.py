from uuid import uuid4

from sqlmodel import Session, select

from app.audit import record_event
from app.models import RequestItem
from app.schemas import WebhookRequest


def ingest_webhook_request(session: Session, payload: WebhookRequest) -> tuple[RequestItem, bool]:
    source_ref = payload.source_ref or f"webhook:{uuid4()}"
    existing = session.exec(
        select(RequestItem).where(
            RequestItem.source_type == "webhook",
            RequestItem.source_ref == source_ref,
        )
    ).first()
    if existing:
        return existing, False
    item = RequestItem(
        source_type="webhook",
        source_ref=source_ref,
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
    )
    session.add(item)
    session.flush()
    record_event(
        session,
        "request.ingested",
        f"Ingested webhook payload {source_ref}",
        request_id=item.id,
        metadata={"source_ref": source_ref, "source_type": "webhook"},
    )
    session.commit()
    session.refresh(item)
    return item, True
