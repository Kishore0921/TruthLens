import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

# Automatically load backend/.env if present, then root .env
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", str(BASE_DIR / "storage")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'truthlens.db'}")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "104857600"))  # 100 MB

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "truthlens-default-secret-key")
FERNET_MASTER_KEY = os.getenv("FERNET_MASTER_KEY", "")

# AI Configuration Flags & Execution Mode
ENABLE_HUGGINGFACE = os.getenv("ENABLE_HUGGINGFACE", "true").lower() in ("true", "1", "yes")
ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "true").lower() in ("true", "1", "yes")
ENABLE_OPENAI = os.getenv("ENABLE_OPENAI", "true").lower() in ("true", "1", "yes")

# Execution mode: hybrid (default), local (offline models only), cloud (external APIs only)
AI_EXECUTION_MODE = os.getenv("AI_EXECUTION_MODE", os.getenv("EXECUTION_MODE", "hybrid")).lower()
if AI_EXECUTION_MODE not in ["local", "cloud", "hybrid"]:
    AI_EXECUTION_MODE = "hybrid"
EXECUTION_MODE = AI_EXECUTION_MODE.upper()

# Environment-based API credentials (configured manually in backend/.env)
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Default models
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
ANTHROPIC_DEFAULT_MODEL = os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
HF_DEFAULT_MODEL = os.getenv("HF_DEFAULT_MODEL", "umm-maybe/AI-image-detector")

# Hardware safeguards (Intel Core i5-4310U, 8GB RAM, CPU-first)
MAX_IMAGE_INFERENCE_DIM = int(os.getenv("MAX_IMAGE_INFERENCE_DIM", "512"))
MAX_VIDEO_SAMPLE_FRAMES = int(os.getenv("MAX_VIDEO_SAMPLE_FRAMES", "10"))
MAX_AUDIO_DURATION_S = float(os.getenv("MAX_AUDIO_DURATION_S", "15.0"))

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".aac"}
ALLOWED_TEXT_EXTENSIONS = {".txt", ".pdf", ".docx"}

ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS |
    ALLOWED_VIDEO_EXTENSIONS |
    ALLOWED_AUDIO_EXTENSIONS |
    ALLOWED_TEXT_EXTENSIONS
)

ORIGINALS_DIR = STORAGE_PATH / "originals"
PROCESSED_DIR = STORAGE_PATH / "processed"
REPORTS_DIR = STORAGE_PATH / "reports"
HF_CACHE_DIR = STORAGE_PATH / "hf_cache"

# Ensure directories exist
for d in [ORIGINALS_DIR, PROCESSED_DIR, REPORTS_DIR, HF_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)
