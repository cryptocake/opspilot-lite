from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "sales_inquiry",
    "support_request",
    "meeting_followup",
    "finance_invoice",
    "internal_task",
    "unknown",
]
Priority = Literal["low", "medium", "high", "urgent"]


class ExtractedEntity(BaseModel):
    name: str
    value: str
    kind: str


class TriageOutput(BaseModel):
    category: Category
    priority: Priority
    confidence: float = Field(ge=0, le=1)
    summary: str
    entities: list[ExtractedEntity] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    needs_human_review: bool = True


class WebhookRequest(BaseModel):
    sender: str | None = None
    subject: str | None = None
    body: str
    source_ref: str | None = None
