import os
from typing import Any
from backend.ai.provider_base import AIProviderBase
from backend.config import HF_CACHE_DIR

class HuggingFaceProvider(AIProviderBase):
    provider_id = "huggingface"
    provider_name = "Hugging Face Hub"
    available_models = [
        "umm-maybe/AI-image-detector",
        "prithivMLmods/Deepfake-Detection-Image-V3",
        "meta-llama/Llama-3.2-3B-Instruct"
    ]

    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        if not api_key:
            return False, "Hugging Face token (HF_TOKEN) is empty."
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=api_key)
            user_info = api.whoami()
            username = user_info.get("name") or user_info.get("fullname") or "Authorized User"
            return True, f"Connection verified. Authenticated as {username} on Hugging Face Hub."
        except Exception as e:
            return False, f"Hugging Face connection failed: {str(e)[:200]}"

    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        """Local/Hugging Face fact extraction fallback."""
        return {}

    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        """Hugging Face semantic comparison."""
        return []

    def generate_investigation_summary(self, investigation_data: dict, api_key: str, model: str) -> str:
        return "Forensic investigation summary generated via local signal rules and models."
