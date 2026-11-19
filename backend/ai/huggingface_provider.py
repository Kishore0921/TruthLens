from typing import Any
from backend.ai.provider_base import AIProviderBase

class HuggingFaceProvider(AIProviderBase):
    provider_id = "huggingface"
    provider_name = "Hugging Face Hub"
    available_models = [
        "meta-llama/Llama-3.2-3B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-7B-Instruct",
        "umm-maybe/AI-image-detector"
    ]

    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        if not api_key:
            return False, "Hugging Face token is empty."
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=api_key)
            user_info = api.whoami()
            username = user_info.get("name") or user_info.get("fullname") or "User"
            return True, f"Connection verified. Authenticated as {username} on Hugging Face Hub."
        except Exception as e:
            return False, f"Hugging Face connection failed: {str(e)[:200]}"

    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        return {}

    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        return []

    def generate_investigation_summary(self, investigation_data: dict, api_key: str, model: str) -> str:
        return "Hugging Face summary generated."
