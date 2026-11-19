from typing import Any, Optional
from huggingface_hub import HfApi
from backend.config import HF_TOKEN

# Catalog of curated multimodal digital forensics and deepfake benchmark datasets
FORENSIC_DATASET_CATALOG = [
    {
        "id": "organika-sdxl-synthetic",
        "repo_id": "Organika/sdxl-detector-dataset",
        "modality": "image",
        "task": "ai_image_detection",
        "description": "Evaluation benchmark of photorealistic SDXL synthetic images vs authentic camera photographs.",
        "license": "openrail",
        "estimated_size": "~1.2 GB",
        "splits": ["train", "test"],
        "recommended_for": "Evaluating ViT and frequency-domain AI image detectors"
    },
    {
        "id": "deepfake-detection-faces",
        "repo_id": "prithivMLmods/Deepfake-Detection-Image-V3",
        "modality": "image",
        "task": "face_manipulation_detection",
        "description": "Curated dataset of authentic vs face-swapped/inpainted portraits across multiple GAN and diffusion generators.",
        "license": "apache-2.0",
        "estimated_size": "~850 MB",
        "splits": ["train", "test"],
        "recommended_for": "Evaluating facial texture and manipulation localization models"
    },
    {
        "id": "faceforensics-video-benchmark",
        "repo_id": "FaceForensics/FaceForensics-Benchmark",
        "modality": "video",
        "task": "video_deepfake_detection",
        "description": "Standard benchmark of pristine videos and paired manipulated face-swapped, Deepfakes, and Face2Face sequences.",
        "license": "research-only",
        "estimated_size": "~4.5 GB",
        "splits": ["train", "validation", "test"],
        "recommended_for": "Evaluating temporal consistency and facial boundary jitter"
    },
    {
        "id": "asvspoof-speech-benchmark",
        "repo_id": "ASVspoof/Synthetic-Speech-2021",
        "modality": "audio",
        "task": "synthetic_speech_detection",
        "description": "International standard acoustic evaluation benchmark for text-to-speech (TTS) and voice conversion detection.",
        "license": "odc-by",
        "estimated_size": "~2.1 GB",
        "splits": ["eval"],
        "recommended_for": "Evaluating neural vocoder spectral cutoff and acoustic silence artifacts"
    }
]

def list_forensic_datasets() -> list[dict[str, Any]]:
    """Return catalog of available digital forensics datasets with metadata."""
    return FORENSIC_DATASET_CATALOG

def get_dataset_info(dataset_id: str) -> Optional[dict[str, Any]]:
    """Fetch metadata and live Hugging Face dataset card info."""
    entry = next((d for d in FORENSIC_DATASET_CATALOG if d["id"] == dataset_id or d["repo_id"] == dataset_id), None)
    if not entry:
        return None

    info = dict(entry)
    info["is_cached_locally"] = False
    
    # Try fetching live metadata from Hugging Face Hub if token or internet available
    try:
        api = HfApi(token=HF_TOKEN or None)
        card_data = api.dataset_info(entry["repo_id"])
        info["downloads"] = getattr(card_data, "downloads", "N/A")
        info["likes"] = getattr(card_data, "likes", 0)
        info["tags"] = getattr(card_data, "tags", [])
        info["last_modified"] = str(getattr(card_data, "lastModified", ""))
    except Exception as e:
        info["hub_status"] = f"Hub query skipped or offline: {str(e)[:80]}"

    return info
