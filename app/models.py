from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RequestStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class RequestItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("source_type", "source_ref", name="uq_request_source"),)

    id: int | None = Field(default=None, primary_key=True)
    source_type: str
    source_ref: str = Field(index=True)
    sender: str | None = None
    subject: str | None = None
    body: str
    status: str = Field(default=RequestStatus.NEW.value, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class TriageResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    request_id: int = Field(index=True, foreign_key="requestitem.id")
    category: str = Field(index=True)
    priority: str
    confidence: float
    summary: str
    extracted_json: str = "{}"
    created_at: datetime = Field(default_factory=utc_now)


class ProposedAction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    request_id: int = Field(index=True, foreign_key="requestitem.id")
    triage_id: int = Field(index=True, foreign_key="triageresult.id")
    action_type: str = Field(index=True)
    title: str
    payload_json: str = "{}"
    status: str = Field(default=ActionStatus.PENDING.value, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    request_id: int | None = Field(default=None, index=True)
    action_id: int | None = Field(default=None, index=True)
    event_type: str = Field(index=True)
    message: str
    metadata_json: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
