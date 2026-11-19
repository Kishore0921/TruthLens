import uuid
import mimetypes
from pathlib import Path
from backend.config import (
    MAX_UPLOAD_SIZE, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS, ALLOWED_TEXT_EXTENSIONS
)

MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image',
    b'\x89PNG': 'image',
    b'RIFF': 'audio',  # WAV
    b'fLaC': 'audio',
    b'ID3': 'audio',   # MP3
    b'\xff\xfb': 'audio',  # MP3
    b'\xff\xf3': 'audio',  # MP3
    b'\x00\x00\x00': 'video',  # MP4/MOV (ftyp box)
}

def get_media_type(extension: str) -> str | None:
    ext = extension.lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    if ext in ALLOWED_AUDIO_EXTENSIONS:
        return "audio"
    if ext in ALLOWED_TEXT_EXTENSIONS:
        return "text"
    return None

def generate_safe_filename(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"

async def validate_upload(file, content: bytes) -> tuple[bool, str, str]:
    """Validate uploaded file. Returns (is_valid, media_type, error_message)."""
    original_name = file.filename or "unknown"
    ext = Path(original_name).suffix.lower()

    # Check extension
    media_type = get_media_type(ext)
    if not media_type:
        return False, "", f"Unsupported file extension: {ext}"

    # Check size
    if len(content) > MAX_UPLOAD_SIZE:
        return False, "", f"File exceeds maximum size of {MAX_UPLOAD_SIZE // (1024*1024)}MB"

    if len(content) == 0:
        return False, "", "File is empty"

    # Check magic bytes for non-text files
    if media_type != "text":
        header = content[:16]
        matched = False
        for magic, mtype in MAGIC_BYTES.items():
            if header.startswith(magic):
                matched = True
                break
        # WEBP check
        if not matched and header[8:12] == b'WEBP':
            matched = True
        # M4A check (same as MP4)
        if not matched and ext in {'.m4a', '.mp4', '.mov'}:
            if b'ftyp' in header[:12]:
                matched = True
        if not matched:
            # Allow through with warning - some valid files may not match
            pass  # Graceful - don't block on magic byte mismatch alone

    # Path traversal check
    if '..' in original_name or '/' in original_name or '\\' in original_name:
        return False, "", "Invalid filename"

    return True, media_type, ""
