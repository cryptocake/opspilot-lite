from sqlmodel import Session, select

from app.errors import NotFoundError
from app.models import ActionStatus, ProposedAction, RequestItem, RequestStatus, TriageResult

OPEN_ACTION_STATUSES = {
    ActionStatus.PENDING.value,
    ActionStatus.APPROVED.value,
    ActionStatus.EDITED.value,
    ActionStatus.FAILED.value,
}
COMPLETED_ACTION_STATUSES = {ActionStatus.EXECUTED.value, ActionStatus.REJECTED.value}

# Below this triage confidence, a request is flagged for manual review: its actions
# must be approved individually rather than via the bulk "approve all" shortcut.
CONFIDENCE_REVIEW_THRESHOLD = 0.6


def triage_needs_review(confidence: float, needs_human_review: bool) -> bool:
    """Whether a triaged request must be reviewed action-by-action by an operator."""
    return bool(needs_human_review) or confidence < CONFIDENCE_REVIEW_THRESHOLD


def determine_request_status(actions: list[ProposedAction], has_triage: bool) -> str:
    if not has_triage:
        return RequestStatus.NEW.value
    if not actions:
        return RequestStatus.TRIAGED.value
    statuses = {action.status for action in actions}
    if ActionStatus.FAILED.value in statuses:
        return RequestStatus.FAILED.value
    if statuses == {ActionStatus.REJECTED.value}:
        return RequestStatus.REJECTED.value
    if statuses <= COMPLETED_ACTION_STATUSES:
        return RequestStatus.COMPLETED.value
    return RequestStatus.PENDING_APPROVAL.value


def recalculate_request_status(session: Session, request_id: int) -> RequestItem:
    request_item = session.get(RequestItem, request_id)
    if not request_item:
        raise NotFoundError(f"Request not found: {request_id}")
    has_triage = session.exec(select(TriageResult.id).where(TriageResult.request_id == request_id)).first() is not None
    actions = session.exec(select(ProposedAction).where(ProposedAction.request_id == request_id)).all()
    request_item.status = determine_request_status(actions, has_triage)
    request_item.touch()
    session.add(request_item)
    return request_item
