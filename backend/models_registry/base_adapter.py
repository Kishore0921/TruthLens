from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field

class ModelPrediction(BaseModel):
    model_id: str
    version: str
    detection_task: str
    score: Optional[float] = None  # Heuristic or model indicator score: 0.0 to 1.0
    confidence_band: str = "medium"  # "low", "medium", "high"
    indicator: str
    description: str
    details: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)

class BaseModelAdapter(ABC):
    def __init__(self, model_id: str, version: str, detection_task: str, provider: str = "TruthLens-Local"):
        self.model_id = model_id
        self.version = version
        self.detection_task = detection_task
        self.provider = provider
        self.is_available = True

    @abstractmethod
    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        """Execute reference-independent detection analysis on the evidence."""
        pass

    def get_info(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "detection_task": self.detection_task,
            "provider": self.provider,
            "is_available": self.is_available,
        }
