import json
from typing import Any
from backend.ai.provider_base import AIProviderBase

class GeminiProvider(AIProviderBase):
    provider_id = "gemini"
    provider_name = "Google Gemini"
    available_models = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    def _get_client(self, api_key: str):
        from google import genai
        return genai.Client(api_key=api_key)

    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        try:
            client = self._get_client(api_key)
            # Lightweight test prompt
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents="Ping. Respond with word 'PONG'."
            )
            if response and response.text:
                return True, f"Connection verified successfully using {model or 'gemini-2.5-flash'}."
            return False, "Received empty response from Gemini API."
        except Exception as e:
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "400" in err_msg:
                return False, "Invalid Google Gemini API key."
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return False, "Google Gemini rate limit / quota exceeded."
            return False, f"Gemini connection failed: {err_msg[:200]}"

    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        prompt = f"""You are a digital forensics structured fact extractor.
Analyze the following reference context and extract structured facts.
Respond ONLY with a valid JSON object matching this schema:
{{
  "event_date": "YYYY-MM-DD or descriptive date or empty",
  "event_time": "time or empty",
  "location": "primary city/country/venue or empty",
  "people": ["name1", "name2"],
  "organizations": ["org1", "org2"],
  "event_type": "conference, summit, speech, press_release, or incident",
  "important_claims": ["claim1", "claim2"]
}}

Context:
\"\"\"{text}\"\"\"
"""
        try:
            client = self._get_client(api_key)
            from google.genai import types
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception:
            return {}

    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        prompt = f"""You are a digital forensics claim verification analyst.
Compare the evidence text against the ground truth reference context.
Identify direct contradictions or strong corroborations.
Respond ONLY with a JSON array of objects:
[
  {{
    "attribute": "location | date | time | person | claim",
    "evidence_claim": "exact quote from evidence",
    "reference_claim": "exact quote from reference",
    "verdict": "CONTRADICTS | SUPPORTS",
    "explanation": "clear factual explanation of the discrepancy or agreement",
    "confidence": "high | medium | low"
  }}
]

Reference Context:
\"\"\"{reference}\"\"\"

Evidence Text:
\"\"\"{text}\"\"\"
"""
        try:
            client = self._get_client(api_key)
            from google.genai import types
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception:
            return []

    def generate_investigation_summary(self, investigation_data: dict, api_key: str, model: str) -> str:
        prompt = f"""You are a senior digital forensics lead drafting an executive summary.
Based on the following structured forensic analysis data, generate a concise, objective 2-paragraph executive investigation summary.
Strict Rules:
- Distinguish observations from verified facts.
- A detection score is an indicator, never a verdict.
- Conclude that findings require qualified human verification.

Data:
{json.dumps(investigation_data, default=str)[:3000]}
"""
        try:
            client = self._get_client(api_key)
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents=prompt
            )
            return response.text or ""
        except Exception as e:
            return f"AI summary generation unavailable ({str(e)[:100]})."
