import json
from dataclasses import dataclass
from typing import Any

from app.models import ProposedAction


@dataclass
class ExecutionResult:
    success: bool
    message: str
    output: dict[str, Any]


class DryRunExecutor:
    def execute(self, action: ProposedAction) -> ExecutionResult:
        payload = json.loads(action.payload_json or "{}")
        return ExecutionResult(
            success=True,
            message=f"Dry-run prepared {action.action_type}",
            output={"action_id": action.id, "action_type": action.action_type, "payload": payload},
        )
