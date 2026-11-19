import os
from typing import Optional, Any
from pathlib import Path
from PIL import Image
from backend.models_registry.base_adapter import BaseModelAdapter, ModelPrediction
from backend.config import HF_CACHE_DIR, HF_TOKEN, MAX_IMAGE_INFERENCE_DIM

class HuggingFaceImageAIDetector(BaseModelAdapter):
    """
    Pretrained AI-Generated Image Detector using Hugging Face repository 'umm-maybe/AI-image-detector'.
    Classifies single images as Artificial / AI-generated (Diffusion, Midjourney, GAN) vs Human-created camera photograph.
    Features lazy loading, CPU execution, local caching, and graceful signal fallback.
    """
    def __init__(self):
        super().__init__(
            model_id="hf_ai_image_detector",
            version="2.0.0",
            detection_task="ai_image_detection",
            provider="HuggingFace-Pretrained",
            modality="image",
            architecture="Vision Transformer (ViT/ConvNeXt)",
            execution_method="local_cpu",
            license="apache-2.0",
            hardware_requirements="CPU-only, downscaled to <=512px, ~300MB RAM",
            limitations=[
                "Model score reflects statistical training distribution on synthetic vs natural photography; not absolute proof of origin",
                "High JPEG recompression or low resolution can degrade feature extraction accuracy",
                "Diffusion inpainting or composite edits may only produce localized or subtle artifacts"
            ]
        )
        self.model_repo = "umm-maybe/AI-image-detector"
        self._pipeline = None
        self._load_failed = False
        self._error_message = None

    def _get_pipeline(self):
        if self._load_failed:
            return None
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import pipeline
            import torch
            # Ensure CPU execution and local caching
            os.environ["HF_HOME"] = str(HF_CACHE_DIR)
            token = HF_TOKEN if HF_TOKEN else None

            self._pipeline = pipeline(
                "image-classification",
                model=self.model_repo,
                token=token,
                device="cpu",
                torch_dtype=torch.float32,
                model_kwargs={"cache_dir": str(HF_CACHE_DIR)}
            )
            return self._pipeline
        except Exception as e:
            self._load_failed = True
            self._error_message = str(e)
            return None

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        classifier = self._get_pipeline()

        # If HF model is unavailable (offline or not downloaded), fallback to graceful notification
        if classifier is None:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="hf_model_unavailable_fallback",
                description=(
                    f"Hugging Face pretrained repository '{self.model_repo}' not locally cached or offline ({self._error_message or 'lazy load skipped'}). "
                    f"Local signal frequency and sensor noise detectors are active."
                ),
                details={"model_repo": self.model_repo, "status": "offline_fallback"},
                limitations=["Pretrained Hugging Face model requires internet for initial weight download or cached weights in storage/hf_cache"]
            )

        try:
            with Image.open(evidence_path) as raw_img:
                img = raw_img.convert("RGB")
                # Downsample if image is huge to avoid CPU RAM spike
                w, h = img.size
                if max(w, h) > MAX_IMAGE_INFERENCE_DIM:
                    scale = MAX_IMAGE_INFERENCE_DIM / max(w, h)
                    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)

            # Inference
            outputs = classifier(img)
            # Output format: [{'label': 'artificial', 'score': 0.98}, {'label': 'human', 'score': 0.02}]
            ai_score = 0.0
            human_score = 0.0
            for item in outputs:
                lbl = item.get("label", "").lower()
                val = float(item.get("score", 0.0))
                if "artificial" in lbl or "fake" in lbl or "ai" in lbl:
                    ai_score = val
                elif "human" in lbl or "real" in lbl:
                    human_score = val

            score = round(ai_score, 3)
            band = "high" if score > 0.8 else ("medium" if score > 0.5 else "low")
            is_ai = score >= 0.5

            desc = (
                f"Hugging Face Pretrained Model '{self.model_repo}' inference completed. "
                f"Predicted: {'Artificial / AI-Generated' if is_ai else 'Human / Authentic'} "
                f"(AI probability: {score * 100:.1f}%, Human probability: {human_score * 100:.1f}%)."
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=score,
                confidence_band=band,
                indicator="hf_ai_generated_image_prediction",
                description=desc,
                details={
                    "model_repo": self.model_repo,
                    "ai_score": score,
                    "human_score": round(human_score, 3),
                    "raw_outputs": outputs
                },
                limitations=[
                    f"Pretrained ViT weights from '{self.model_repo}' are probabilistic indicators on synthetic patterns",
                    "Novel generative architectures (unseen during training) can produce false negatives",
                    "Aggressive compression, camera lens distortion, and digital noise can impact model confidence"
                ]
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="hf_inference_error",
                description=f"Hugging Face model inference error: {str(e)}",
                details={"error": str(e)},
                limitations=["Inference pipeline error on provided image tensor"]
            )
