import base64
import os
from cryptography.fernet import Fernet
from backend.config import FERNET_MASTER_KEY, APP_SECRET_KEY

def _get_fernet_instance() -> Fernet:
    key = FERNET_MASTER_KEY
    if not key:
        # Generate safe key derived from APP_SECRET_KEY if not explicitly specified
        seed = (APP_SECRET_KEY + "truthlens_master_salt_2026").encode()
        padded = (seed * 4)[:32]
        key = base64.urlsafe_b64encode(padded).decode()
    elif isinstance(key, str):
        key = key.strip()
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string at rest using Fernet symmetric encryption."""
    if not plaintext:
        return ""
    f = _get_fernet_instance()
    encrypted_bytes = f.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret string at rest using Fernet."""
    if not ciphertext:
        return ""
    f = _get_fernet_instance()
    decrypted_bytes = f.decrypt(ciphertext.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")

def mask_secret(secret: str) -> str:
    """
    Format an API key for safe UI presentation without leaking the secret.
    e.g. sk-proj-...789a or AIza...f12b
    """
    if not secret:
        return ""
    s = secret.strip()
    if len(s) <= 8:
        return "****"
    if s.startswith("sk-"):
        prefix = s[:7]
    elif s.startswith("AIza"):
        prefix = s[:6]
    else:
        prefix = s[:4]
    suffix = s[-4:]
    return f"{prefix}...{suffix}"
