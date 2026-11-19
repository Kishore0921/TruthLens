from typing import Optional, Any
from backend.models_registry.base_adapter import BaseModelAdapter
from backend.models_registry.image_ai_detector import FrequencyArtifactDetector, LocalNoiseVarianceDetector
from backend.models_registry.deepfake_detector import VideoTemporalConsistencyDetector
from backend.models_registry.audio_spoof_detector import SyntheticAudioDetector

class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None

    def __init__(self):
        self._adapters: dict[str, BaseModelAdapter] = {}
        self._register_default_adapters()

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = ModelRegistry()
        return cls._instance

    def _register_default_adapters(self):
        self.register(FrequencyArtifactDetector())
        self.register(LocalNoiseVarianceDetector())
        self.register(VideoTemporalConsistencyDetector())
        self.register(SyntheticAudioDetector())

    def register(self, adapter: BaseModelAdapter):
        self._adapters[adapter.model_id] = adapter

    def get_model(self, model_id: str) -> Optional[BaseModelAdapter]:
        return self._adapters.get(model_id)

    def list_models(self) -> list[dict[str, Any]]:
        return [adapter.get_info() for adapter in self._adapters.values()]

    def get_models_for_task(self, detection_task: str) -> list[BaseModelAdapter]:
        return [adapter for adapter in self._adapters.values() if adapter.detection_task == detection_task]
