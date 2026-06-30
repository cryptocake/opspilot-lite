import json
from typing import Any

import httpx

from app.errors import LLMError


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, dict):
                return content
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"Provider {self.model} returned a response that was not valid triage JSON") from exc
