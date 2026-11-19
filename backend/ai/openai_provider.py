import json
import base64
import os
from pathlib import Path
from typing import Any, Optional
from backend.ai.provider_base import AIProviderBase

class OpenAIProvider(AIProviderBase):
    provider_id = "openai"
    provider_name = "OpenAI"
    available_models = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo"
    ]

    def _get_client(self, api_key: str):
        from openai import OpenAI
        return OpenAI(api_key=api_key, timeout=25.0)

    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        if not api_key:
            return False, "OpenAI API key is empty."
        try:
            client = self._get_client(api_key)
            completion = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "Ping"}],
                max_tokens=5
            )
            if completion and completion.choices:
                return True, f"Connection verified successfully using {model or 'gpt-4o-mini'}."
            return False, "Received empty completion from OpenAI API."
        except Exception as e:
            err_msg = str(e)
            if "Incorrect API key" in err_msg or "401" in err_msg:
                return False, "Invalid OpenAI API key."
            if "RateLimitError" in err_msg or "429" in err_msg:
                return False, "OpenAI rate limit or quota exceeded."
            return False, f"OpenAI connection failed: {err_msg[:200]}"

    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        """Extract structured entities, dates, locations and key claims from text context."""
        prompt = f"""You are a digital forensics fact extractor.
Analyze the reference text and output valid JSON only:
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
            completion = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=600
            )
            return json.loads(completion.choices[0].message.content or "{}")
        except Exception:
            return {}

    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        """Compare evidence text against ground-truth reference context to identify contradictions."""
        prompt = f"""You are a digital forensics claim verification analyst.
Compare the evidence text against the ground truth reference context.
Output JSON format:
{{
  "comparisons": [
    {{
      "attribute": "location | date | time | person | claim",
      "evidence_claim": "exact quote from evidence",
      "reference_claim": "exact quote from reference",
      "verdict": "CONTRADICTS | SUPPORTS",
      "explanation": "clear factual explanation of the discrepancy or agreement",
      "confidence": "high | medium | low"
    }}
  ]
}}

Reference:
\"\"\"{reference}\"\"\"

Evidence:
\"\"\"{text}\"\"\"
"""
        try:
            client = self._get_client(api_key)
            completion = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            data = json.loads(completion.choices[0].message.content or "{}")
            return data.get("comparisons", [])
        except Exception:
            return []

    def inspect_visual_context(self, image_path: str, api_key: str, model: str) -> dict[str, Any]:
        """Multimodal visual inspection using gpt-4o vision."""
        try:
            from PIL import Image
            import io
            client = self._get_client(api_key)
            
            with Image.open(image_path) as pil_img:
                pil_img.thumbnail((512, 512))
                buf = io.BytesIO()
                pil_img.convert("RGB").save(buf, format="JPEG", quality=80)
                b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

            prompt = (
                "You are a digital forensics visual analyst. Inspect this image. "
                "Describe visible key objects, scene setting, environmental lighting, visible signage or text, "
                "and identifiable landmarks. Provide objective observations only. "
                "Do NOT proclaim whether the image is authentic or fake. Respond in 2-3 sentences."
            )
            response = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]
                    }
                ],
                max_tokens=300
            )
            return {
                "visual_summary": response.choices[0].message.content or "",
                "model": model or "gpt-4o-mini"
            }
        except Exception as e:
            return {"error": str(e)}

    def inspect_audio_context(self, audio_path: str, api_key: str, model: str) -> dict[str, Any]:
        """Audio context transcription using whisper-1."""
        try:
            client = self._get_client(api_key)
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return {
                "transcription": getattr(transcription, "text", "") or "",
                "model": "whisper-1"
            }
        except Exception as e:
            return {"error": str(e)}

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
            completion = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return completion.choices[0].message.content or ""
        except Exception as e:
            return f"AI summary generation unavailable ({str(e)[:100]})."
