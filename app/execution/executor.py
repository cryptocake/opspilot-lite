from typing import Any

from sqlmodel import Session

from app.audit import record_event
from app.errors import InvalidStateError, NotFoundError
from app.execution.dry_run import ExecutionResult
from app.execution.factory import get_action_executor
from app.models import ActionStatus, ProposedAction
from app.request_state import recalculate_request_status

EXECUTABLE_STATUSES = {ActionStatus.APPROVED.value, ActionStatus.EDITED.value}


def execute_action(session: Session, action_id: int, executor: Any | None = None) -> ExecutionResult:
    action = session.get(ProposedAction, action_id)
    if not action:
        raise NotFoundError(f"Action not found: {action_id}")
    if action.status not in EXECUTABLE_STATUSES:
        raise InvalidStateError(f"Action {action_id} is not approved for execution")
    executor = executor or get_action_executor()
    try:
        result = executor.execute(action)
    except Exception as exc:
        action.status = ActionStatus.FAILED.value
        action.touch()
        record_event(session, "action.failed", str(exc), request_id=action.request_id, action_id=action.id)
        session.add(action)
        recalculate_request_status(session, action.request_id)
        session.commit()
        raise
    action.status = ActionStatus.EXECUTED.value if result.success else ActionStatus.FAILED.value
    action.touch()
    record_event(
        session,
        "action.executed" if result.success else "action.failed",
        result.message,
        request_id=action.request_id,
        action_id=action.id,
        metadata=result.output,
    )
    session.add(action)
    recalculate_request_status(session, action.request_id)
    session.commit()
    session.refresh(action)
    return result
