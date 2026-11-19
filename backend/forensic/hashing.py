import hashlib
from pathlib import Path
import cv2
import numpy as np

def compute_sha256(filepath: str | Path) -> str:
    """Compute SHA-256 cryptographic hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def compute_phash(filepath: str | Path) -> str:
    """
    Compute 64-bit perceptual hash (pHash) using 2D Discrete Cosine Transform (DCT).
    pHash enables detection of near-duplicate, resized, recompressed, or format-converted images.
    """
    try:
        img = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return ""
        resized = cv2.resize(img, (32, 32), interpolation=cv2.INTER_AREA)
        f_arr = np.float32(resized)
        dct = cv2.dct(f_arr)
        dct_low = dct[:8, :8]
        # Compare against median of AC coefficients
        med = float(np.median(dct_low))
        bits = (dct_low > med).flatten()
        hash_val = 0
        for bit in bits:
            hash_val = (hash_val << 1) | int(bit)
        return f"{hash_val:016x}"
    except Exception:
        return ""
