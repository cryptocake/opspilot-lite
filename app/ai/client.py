from typing import Protocol


class LLMClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Return a JSON-compatible dictionary from an LLM call."""
