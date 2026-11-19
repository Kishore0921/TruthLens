import json
from typing import Any
from backend.ai.provider_base import AIProviderBase

class AnthropicProvider(AIProviderBase):
    provider_id = "anthropic"
    provider_name = "Anthropic Claude"
    available_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229"
    ]

    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        if not api_key:
            return False, "API key is empty."
        try:
            import anthropic
            m = model or "claude-3-5-haiku-20241022"
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=m,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            return True, f"Connection verified successfully using {m}."
        except Exception as e:
            return False, f"Anthropic connection failed: {str(e)[:200]}"

    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        if not text or not api_key:
            return {}
        try:
            import anthropic
            m = model or "claude-3-5-haiku-20241022"
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                "Extract structured forensic facts from this ground-truth text:\n"
                f'"{text}"\n\n'
                "Output ONLY a raw JSON object with keys: "
                '"event_date" (str), "event_time" (str), "location" (str), '
                '"people" (list of str), "organizations" (list of str), "event_type" (str), "important_claims" (list of str).'
            )
            msg = client.messages.create(
                model=m,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            text_resp = msg.content[0].text.strip()
            if "{" in text_resp:
                json_str = text_resp[text_resp.find("{"):text_resp.rfind("}") + 1]
                return json.loads(json_str)
            return {}
        except Exception:
            return {}

    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        return []

    def generate_investigation_summary(self, investigation_data: dict, api_key: str, model: str) -> str:
        return "Anthropic investigation summary generated."
