import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Load .env if present
load_dotenv(BASE_DIR / ".env")

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", str(BASE_DIR / "storage")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'truthlens.db'}")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "104857600")) # 100 MB

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "truthlens-default-secret-key")
FERNET_MASTER_KEY = os.getenv("FERNET_MASTER_KEY", "")

GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

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
