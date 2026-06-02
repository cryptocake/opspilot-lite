import json
from typing import Any

import httpx

from app.execution.dry_run import ExecutionResult
from app.models import ProposedAction


class WebhookExecutor:
    def __init__(self, sink_url: str, timeout_seconds: float = 10.0):
        self.sink_url = sink_url
        self.timeout_seconds = timeout_seconds

    def execute(self, action: ProposedAction) -> ExecutionResult:
        payload = json.loads(action.payload_json or "{}")
        envelope = {
            "request_id": action.request_id,
            "action_id": action.id,
            "action_type": action.action_type,
            "title": action.title,
            "payload": payload,
        }
        response = httpx.post(self.sink_url, json=envelope, timeout=self.timeout_seconds)
        response.raise_for_status()
        return ExecutionResult(
            success=True,
            message=f"Delivered {action.action_type} to configured webhook sink",
            output={
                "action_id": action.id,
                "action_type": action.action_type,
                "payload": payload,
                "sink_url": self.sink_url,
                "response_status": response.status_code,
                "response_body": _response_body(response),
            },
        )


def _response_body(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text
