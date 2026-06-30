from sqlmodel import Session

from app.audit import record_event
from app.models import ProposedAction, RequestItem, TriageResult
from app.schemas import TriageOutput
from app.workflows.definitions import (
    checklist_payload,
    draft_reply_payload,
    meeting_summary_payload,
    payload,
    task_payload,
)


def route_workflow(
    session: Session,
    request_item: RequestItem,
    triage_result: TriageResult,
    triage: TriageOutput,
) -> list[ProposedAction]:
    specs = _action_specs(triage)
    actions: list[ProposedAction] = []
    for action_type, title, data in specs:
        action = ProposedAction(
            request_id=request_item.id,
            triage_id=triage_result.id,
            action_type=action_type,
            title=title,
            payload_json=payload(data),
        )
        session.add(action)
        session.flush()
        record_event(
            session,
            "action.proposed",
            f"Proposed {action_type}: {title}",
            request_id=request_item.id,
            action_id=action.id,
        )
        actions.append(action)
    return actions


def _action_specs(triage: TriageOutput) -> list[tuple[str, str, dict]]:
    if triage.category == "sales_inquiry":
        return [
            ("draft_reply", "Draft response to sales inquiry", draft_reply_payload(triage)),
            ("create_discovery_checklist", "Create automation discovery checklist", checklist_payload(triage)),
        ]
    if triage.category == "support_request":
        return [
            ("draft_reply", "Draft support acknowledgement", draft_reply_payload(triage)),
            ("create_task", "Create support follow-up task", task_payload(triage)),
        ]
    if triage.category == "meeting_followup":
        return [
            ("summarize_meeting", "Summarize meeting and decisions", meeting_summary_payload(triage)),
            ("create_task", "Create meeting follow-up task", task_payload(triage)),
        ]
    if triage.category == "finance_invoice":
        return [
            ("draft_reply", "Draft finance acknowledgement", draft_reply_payload(triage)),
            ("create_task", "Create finance review task", task_payload(triage)),
        ]
    if triage.category == "internal_task":
        return [("create_task", "Create internal task", task_payload(triage))]
    return [("draft_reply", "Draft human review response", draft_reply_payload(triage))]
