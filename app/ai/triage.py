from app.ai.client import LLMClient
from app.ai.prompts import TRIAGE_SYSTEM_PROMPT
from app.models import RequestItem
from app.schemas import TriageOutput


def triage_request(llm_client: LLMClient, request_item: RequestItem) -> TriageOutput:
    user_prompt = (
        f"Subject: {request_item.subject or ''}\n"
        f"Sender: {request_item.sender or ''}\n"
        f"Body:\n{request_item.body}"
    )
    raw = llm_client.complete_json(TRIAGE_SYSTEM_PROMPT, user_prompt)
    return TriageOutput.model_validate(raw)
