import json
from pathlib import Path

def extract_image_metadata(filepath: str) -> dict:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        with Image.open(filepath) as img:
            metadata = {
                "format": img.format,
                "mode": img.mode,
                "width": img.size[0],
                "height": img.size[1],
            }
            exif_data = img.getexif()
            if exif_data:
                exif = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    try:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='replace')
                        json.dumps(value)  # Test serializable
                        exif[str(tag)] = value
                    except (TypeError, ValueError):
                        exif[str(tag)] = str(value)
                metadata["exif"] = exif
            else:
                metadata["exif"] = {}
                metadata["exif_note"] = "No EXIF data found. This is common for screenshots, web-downloaded images, and images that have been processed. Absence of EXIF does not indicate manipulation."
            return metadata
    except Exception as e:
        return {"error": str(e)}

def extract_video_metadata(filepath: str) -> dict:
    metadata = {}
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            import json as json_mod
            probe = json_mod.loads(result.stdout)
            fmt = probe.get("format", {})
            metadata["duration"] = float(fmt.get("duration", 0))
            metadata["format_name"] = fmt.get("format_name", "unknown")
            metadata["size"] = int(fmt.get("size", 0))
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    metadata["width"] = stream.get("width")
                    metadata["height"] = stream.get("height")
                    metadata["codec"] = stream.get("codec_name")
                    metadata["fps"] = stream.get("r_frame_rate")
                    nb_frames = stream.get("nb_frames")
                    if nb_frames and nb_frames != "N/A":
                        metadata["frame_count"] = int(nb_frames)
            return metadata
    except FileNotFoundError:
        pass  # ffprobe not available, fall back to OpenCV
    except Exception:
        pass

    # OpenCV fallback
    try:
        import cv2
        cap = cv2.VideoCapture(filepath)
        if cap.isOpened():
            metadata["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            metadata["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            metadata["fps"] = cap.get(cv2.CAP_PROP_FPS)
            metadata["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if metadata["fps"] and metadata["fps"] > 0 and metadata["frame_count"]:
                metadata["duration"] = metadata["frame_count"] / metadata["fps"]
            metadata["note"] = "Metadata extracted via OpenCV fallback (ffprobe not available). Some fields may be approximate."
            cap.release()
        return metadata
    except Exception as e:
        return {"error": str(e), "note": "Neither ffprobe nor OpenCV could extract metadata."}

def extract_audio_metadata(filepath: str) -> dict:
    try:
        import soundfile as sf
        info = sf.info(filepath)
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "subtype": info.subtype,
        }
    except Exception:
        pass
    try:
        import librosa
        y, sr = librosa.load(filepath, sr=None, duration=60)
        return {
            "duration": len(y) / sr,
            "sample_rate": sr,
            "channels": 1,
            "note": "Metadata from librosa fallback (mono load)."
        }
    except Exception as e:
        return {"error": str(e)}
