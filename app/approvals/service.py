import json
from typing import Any

from sqlmodel import Session

from app.audit import record_event
from app.errors import InvalidStateError, NotFoundError
from app.models import ActionStatus, ProposedAction
from app.request_state import recalculate_request_status

APPROVABLE_STATUSES = {
    ActionStatus.PENDING.value,
    ActionStatus.EDITED.value,
    ActionStatus.FAILED.value,
}
EDITABLE_STATUSES = {
    ActionStatus.PENDING.value,
    ActionStatus.APPROVED.value,
    ActionStatus.EDITED.value,
    ActionStatus.FAILED.value,
}
REJECTABLE_STATUSES = {
    ActionStatus.PENDING.value,
    ActionStatus.APPROVED.value,
    ActionStatus.EDITED.value,
    ActionStatus.FAILED.value,
}


def _get_action(session: Session, action_id: int) -> ProposedAction:
    action = session.get(ProposedAction, action_id)
    if not action:
        raise NotFoundError(f"Action not found: {action_id}")
    return action


def _require_status(action: ProposedAction, allowed_statuses: set[str], operation: str) -> None:
    if action.status not in allowed_statuses:
        allowed = ", ".join(sorted(allowed_statuses))
        raise InvalidStateError(
            f"Action {action.id} cannot be {operation} from status {action.status}; allowed statuses: {allowed}"
        )


def approve_action(session: Session, action_id: int) -> ProposedAction:
    action = _get_action(session, action_id)
    _require_status(action, APPROVABLE_STATUSES, "approved")
    action.status = ActionStatus.APPROVED.value
    action.touch()
    record_event(
        session,
        "action.approved",
        f"Approved action {action.id}",
        request_id=action.request_id,
        action_id=action.id,
    )
    session.add(action)
    recalculate_request_status(session, action.request_id)
    session.commit()
    session.refresh(action)
    return action


def reject_action(session: Session, action_id: int, reason: str = "") -> ProposedAction:
    action = _get_action(session, action_id)
    _require_status(action, REJECTABLE_STATUSES, "rejected")
    action.status = ActionStatus.REJECTED.value
    action.touch()
    record_event(
        session,
        "action.rejected",
        f"Rejected action {action.id}",
        request_id=action.request_id,
        action_id=action.id,
        metadata={"reason": reason},
    )
    session.add(action)
    recalculate_request_status(session, action.request_id)
    session.commit()
    session.refresh(action)
    return action


def edit_action(session: Session, action_id: int, new_payload: dict[str, Any]) -> ProposedAction:
    action = _get_action(session, action_id)
    _require_status(action, EDITABLE_STATUSES, "edited")
    action.payload_json = json.dumps(new_payload, sort_keys=True)
    action.status = ActionStatus.EDITED.value
    action.touch()
    record_event(
        session,
        "action.edited",
        f"Edited action {action.id}",
        request_id=action.request_id,
        action_id=action.id,
        metadata={"payload": new_payload},
    )
    session.add(action)
    recalculate_request_status(session, action.request_id)
    session.commit()
    session.refresh(action)
    return action
