from abc import ABC, abstractmethod
from typing import Any

class AIProviderBase(ABC):
    provider_id: str
    provider_name: str
    available_models: list[str]

    @abstractmethod
    def test_connection(self, api_key: str, model: str) -> tuple[bool, str]:
        """Test API key connection. Returns (success: bool, message: str)."""
        pass

    @abstractmethod
    def extract_structured_facts(self, text: str, api_key: str, model: str) -> dict[str, Any]:
        """Extract structured reference facts from context text."""
        pass

    @abstractmethod
    def compare_claims(self, text: str, reference: str, api_key: str, model: str) -> list[dict[str, Any]]:
        """Perform semantic claim comparison between evidence text and reference facts."""
        pass

    @abstractmethod
    def generate_investigation_summary(self, investigation_data: dict, api_key: str, model: str) -> str:
        """Generate executive forensic summary."""
        pass
