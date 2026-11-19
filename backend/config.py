import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", str(BASE_DIR / "storage")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'truthlens.db'}")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "104857600"))

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}
ALLOWED_TEXT_EXTENSIONS = {".txt"}

ALL_ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS | ALLOWED_TEXT_EXTENSIONS

ORIGINALS_DIR = STORAGE_PATH / "originals"
PROCESSED_DIR = STORAGE_PATH / "processed"
REPORTS_DIR = STORAGE_PATH / "reports"
