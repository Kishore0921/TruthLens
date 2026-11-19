"""
TruthLens Image CNN — Prediction Interface
===========================================
Loads the trained checkpoint and runs inference on a single image.
Returns structured JSON with model metadata and class scores.
"""
import sys
import json
import torch
from pathlib import Path
from PIL import Image
from torchvision import transforms
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from model import TruthLensImageCNN

IMAGE_SIZE = 128
CLASS_MAP = {0: "REAL", 1: "AI_GENERATED"}
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "truthlens_image_cnn.pth"

_inference_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

_model = None
_device = None


def load_model(checkpoint_path: str = None):
    """Lazy-load the trained model checkpoint."""
    global _model, _device
    if _model is not None:
        return _model, _device

    ckpt_path = Path(checkpoint_path) if checkpoint_path else CHECKPOINT_PATH
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Trained checkpoint not found at: {ckpt_path}")

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _model = TruthLensImageCNN(num_classes=2)
    ckpt = torch.load(str(ckpt_path), map_location=_device, weights_only=False)
    _model.load_state_dict(ckpt["model_state_dict"])
    _model.to(_device)
    _model.eval()
    return _model, _device


@torch.no_grad()
def predict_image(image_path: str, checkpoint_path: str = None) -> dict:
    """
    Run inference on a single image.

    Returns a structured prediction dict with class scores and model metadata.
    """
    model, device = load_model(checkpoint_path)

    img = Image.open(image_path).convert("RGB")
    tensor = _inference_transform(img).unsqueeze(0).to(device)

    logits = model(tensor)
    probs = torch.softmax(logits, dim=1).squeeze(0)

    real_score = float(probs[0])
    ai_score = float(probs[1])
    predicted_label = CLASS_MAP[int(probs.argmax())]

    return {
        "model_name": "TruthLens Image CNN",
        "model_version": "1.0",
        "predicted_class": predicted_label,
        "class_scores": {
            "REAL": round(real_score, 6),
            "AI_GENERATED": round(ai_score, 6),
        },
        "model_type": "custom_cnn_trained_from_scratch",
        "input_image": str(image_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "warning": "Uncalibrated model scores are not definitive forensic evidence.",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python predict.py <image_path>")
        sys.exit(1)

    result = predict_image(sys.argv[1])
    print(json.dumps(result, indent=2))
