"""
TruthLens Custom CNN Image Forensic Model Adapter
==================================================
Integrates the genuinely scratch-trained TruthLens Image CNN into the
TruthLens backend model registry.

Model Type: 4-Block CNN with BatchNorm, GAP and Dropout
Weights: Trained from scratch on GenImage dataset (no pretrained transfer)
Input Size: 128x128 RGB
Task: AI-generated vs authentic camera image detection
"""
from pathlib import Path
from typing import Optional, Any
from PIL import Image

try:
    import torch
    from torchvision import transforms
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    transforms = None
    TORCH_AVAILABLE = False

from backend.models_registry.base_adapter import BaseModelAdapter, ModelPrediction

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_CHECKPOINT_PATH = BASE_DIR / "image_model_training" / "models" / "truthlens_image_cnn.pth"
IMAGE_SIZE = 128

_transform = (
    transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    if TORCH_AVAILABLE
    else None
)


class TruthLensScratchImageCNN(BaseModelAdapter):
    """
    Independent custom deep learning image classifier trained from scratch on GenImage.
    Gracefully skips local PyTorch execution on low-RAM cloud deployments.
    """
    def __init__(self):
        super().__init__(
            model_id="truthlens_custom_image_cnn",
            version="1.0.0",
            detection_task="ai_image_detection",
            provider="TruthLens-InHouse",
            modality="image",
            architecture="Custom 4-Block CNN (Conv-BN-ReLU-MaxPool) + GAP",
            execution_method="local_cpu",
            license="Apache-2.0",
            hardware_requirements="CPU-compatible, ~50MB RAM footprint, 128x128 input",
            limitations=[
                "Trained from scratch on GenImage benchmark (BigGAN, ADM, Midjourney); scores reflect generative texture patterns",
                "Uncalibrated model scores are heuristic indicators and not conclusive legal proof of artificial origin",
                "Does not detect targeted Photoshop inpainting, copy-move splicing, or face swaps (requires localization models)",
                "Heavily compressed or blurred images can attenuate high-frequency generative artifacts"
            ]
        )
        self._model = None
        self._device = None

    def _load_model(self):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch runtime disabled on lightweight cloud deployment")

        if self._model is not None:
            return self._model, self._device

        if not MODEL_CHECKPOINT_PATH.exists():
            raise FileNotFoundError(f"Model weights not found at {MODEL_CHECKPOINT_PATH}")

        from image_model_training.scripts.model import TruthLensImageCNN

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = TruthLensImageCNN(num_classes=2)
        ckpt = torch.load(str(MODEL_CHECKPOINT_PATH), map_location=self._device, weights_only=False)
        self._model.load_state_dict(ckpt["model_state_dict"])
        self._model.to(self._device)
        self._model.eval()
        self.download_status = "ready"
        return self._model, self._device

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        if not TORCH_AVAILABLE or not MODEL_CHECKPOINT_PATH.exists():
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="model_unavailable",
                description="Custom Scratch CNN skipped on lightweight cloud runtime; relying on signal/ELA and cloud AI adapters.",
                details={"torch_available": TORCH_AVAILABLE, "weights_present": MODEL_CHECKPOINT_PATH.exists()},
                limitations=["Local PyTorch runtime skipped to conserve server memory"]
            )

        try:
            model, device = self._load_model()
            with Image.open(evidence_path) as img:
                img_rgb = img.convert("RGB")
                tensor = _transform(img_rgb).unsqueeze(0).to(device)

            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1).squeeze(0)

            real_score = float(probs[0].item())
            ai_score = float(probs[1].item())

            margin = abs(ai_score - real_score)
            if margin > 0.6:
                confidence_band = "high"
            elif margin > 0.25:
                confidence_band = "medium"
            else:
                confidence_band = "low"

            is_ai = ai_score > 0.5
            indicator = "ai_generation_indicators" if is_ai else "photographic_features"
            verdict_desc = "AI-generated image patterns detected" if is_ai else "Natural camera photographic characteristics detected"

            desc = (
                f"Custom Scratch CNN Assessment: {verdict_desc}. "
                f"Model score: AI={ai_score:.3f}, Real={real_score:.3f} (confidence band: {confidence_band})."
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=round(ai_score, 4),
                confidence_band=confidence_band,
                indicator=indicator,
                description=desc,
                details={
                    "real_score": round(real_score, 4),
                    "ai_generated_score": round(ai_score, 4),
                    "architecture": self.architecture,
                    "input_resolution": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
                    "training_basis": "GenImage (BigGAN, ADM, Midjourney)",
                },
                limitations=self.limitations
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="model_error",
                description=f"Custom CNN inference failed: {str(e)}",
                details={"error": str(e)},
                limitations=["Model inference failed gracefully"]
            )
