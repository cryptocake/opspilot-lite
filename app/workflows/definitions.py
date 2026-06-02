import json

from app.schemas import TriageOutput


def payload(data: dict) -> str:
    return json.dumps(data, sort_keys=True)


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith(('.', '!', '?')) else f"{text}."


def draft_reply_payload(triage: TriageOutput) -> dict:
    return {
        "reply": (
            "Thanks for reaching out. I reviewed your request: "
            f"{_sentence(triage.summary)} I'll follow up with the right next steps."
        ),
        "summary": triage.summary,
        "category": triage.category,
    }


def task_payload(triage: TriageOutput) -> dict:
    return {
        "title": f"Follow up on: {triage.summary}",
        "priority": str(triage.priority).title(),
        "entities": [entity.model_dump() for entity in triage.entities],
    }


def checklist_payload(triage: TriageOutput) -> dict:
    systems = [entity.value for entity in triage.entities if entity.kind == "system"]
    return {
        "title": "Automation discovery checklist",
        "questions": [
            "Confirm the systems that need to be connected",
            "Identify the trigger that starts the workflow",
            "Define what should happen on success and failure",
            "Confirm who approves production changes",
        ],
        "systems_detected": systems,
    }


def meeting_summary_payload(triage: TriageOutput) -> dict:
    return {"summary": triage.summary, "next_step": "Confirm owners, deadlines, and launch blockers."}
