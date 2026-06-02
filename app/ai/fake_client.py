import re


class FakeLLMClient:
    """Deterministic client for demos and tests."""

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        text = user_prompt.lower()
        systems = self._systems(user_prompt)
        if any(word in text for word in ["broken", "error", "api key", "stopped working", "failed"]):
            return self._result(
                "support_request",
                "high",
                0.91,
                user_prompt,
                systems,
                ["draft_reply", "create_task"],
            )
        if any(word in text for word in ["meeting notes", "action items", " owns ", "launch target"]):
            return self._result(
                "meeting_followup",
                "medium",
                0.88,
                user_prompt,
                systems,
                ["summarize_meeting", "create_task"],
            )
        if any(word in text for word in ["invoice", "payment", "receipt"]):
            return self._result(
                "finance_invoice",
                "medium",
                0.86,
                user_prompt,
                systems,
                ["extract_invoice", "draft_reply"],
            )
        if any(
            word in text
            for word in ["shopify", "hubspot", "typeform", "automation", "airtable", "slack"]
        ):
            return self._result(
                "sales_inquiry",
                "medium",
                0.9,
                user_prompt,
                systems,
                ["draft_reply", "create_discovery_checklist"],
            )
        return self._result("unknown", "low", 0.55, user_prompt, systems, ["draft_reply"])

    def _systems(self, text: str) -> list[dict[str, str]]:
        known = ["Shopify", "Airtable", "Slack", "HubSpot", "Typeform", "Stripe", "GitHub", "Notion"]
        found = []
        for name in known:
            if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
                found.append({"name": name, "value": name, "kind": "system"})
        return found

    def _result(
        self,
        category: str,
        priority: str,
        confidence: float,
        text: str,
        entities: list[dict],
        actions: list[str],
    ) -> dict:
        cleaned = re.sub(r"Subject:.*?Body:\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        summary = " ".join(cleaned.strip().split())[:180]
        return {
            "category": category,
            "priority": priority,
            "confidence": confidence,
            "summary": summary,
            "entities": entities,
            "recommended_actions": actions,
            "needs_human_review": True,
        }
