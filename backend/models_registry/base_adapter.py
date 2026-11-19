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
    def __init__(
        self,
        model_id: str,
        version: str,
        detection_task: str,
        provider: str = "TruthLens-Local",
        modality: str = "image",
        architecture: str = "Signal Forensics",
        execution_method: str = "local_cpu",
        license: str = "Apache-2.0",
        hardware_requirements: str = "CPU-only, <250MB RAM",
        limitations: Optional[list[str]] = None
    ):
        self.model_id = model_id
        self.version = version
        self.detection_task = detection_task
        self.provider = provider
        self.modality = modality
        self.architecture = architecture
        self.execution_method = execution_method
        self.license = license
        self.hardware_requirements = hardware_requirements
        self.limitations = limitations or []
        self.is_available = True
        self.download_status = "ready"
        self.inference_status = "idle"

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
            "modality": self.modality,
            "architecture": self.architecture,
            "execution_method": self.execution_method,
            "license": self.license,
            "hardware_requirements": self.hardware_requirements,
            "is_available": self.is_available,
            "download_status": self.download_status,
            "inference_status": self.inference_status,
            "limitations": self.limitations,
        }
