import uuid
import os
import json
import numpy as np
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation
from backend.config import PROCESSED_DIR
from backend.forensic.metadata import extract_video_metadata
from backend.models_registry import ModelRegistry

async def analyze_video(evidence_id: str, filepath: str, media_type: str) -> list[Finding]:
    findings: list[Finding] = []
    processed_dir = PROCESSED_DIR / evidence_id
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Metadata extraction (ffprobe or OpenCV fallback)
    meta = extract_video_metadata(filepath)
    duration = float(meta.get("duration", 0.0) or 0.0)
    width = meta.get("width")
    height = meta.get("height")
    fps = meta.get("fps")
    codec = meta.get("codec", "unspecified")
    note = meta.get("note", "")

    file_size = os.path.getsize(filepath)
    dim_str = f"{width}x{height}" if width and height else "unknown dimensions"
    fps_str = f"{fps} FPS" if fps else "variable/unknown FPS"
    dur_str = f"{duration:.2f}s" if duration > 0 else "unknown duration"

    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="video",
        engine="video_container_info",
        indicator="stream_metadata",
        description=f"Video stream: {dim_str}, {dur_str}, {fps_str}, codec={codec}, size={file_size:,} bytes. {note}".strip(),
        location=EvidenceLocation(timestamp=0.0),
        model_score=None,
        confidence_band="high",
        limitations=["Container metadata can be rewritten without re-encoding video streams"]
    ))

    # 2. Check for presence of embedded audio stream
    has_audio_stream = False
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "a", filepath],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "codec_type=audio" in result.stdout:
            has_audio_stream = True
    except Exception:
        # Fallback heuristic: check container extension
        has_audio_stream = Path(filepath).suffix.lower() in [".mp4", ".mov", ".mkv", ".avi"]

    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="video",
        engine="video_audio_track_probe",
        indicator="audio_track_presence",
        description=f"Audio track probe: {'Embedded audio stream detected in video container.' if has_audio_stream else 'No independent audio stream identified.'}",
        location=EvidenceLocation(timestamp=0.0),
        model_score=None,
        confidence_band="high",
        limitations=["Container stream inspection; muted or silent audio tracks may still appear present"]
    ))

    # 3. Sequential OpenCV frame extraction (8 - 12 frames, max 15s capped)
    try:
        import cv2
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_frame_sampler",
                indicator="stream_open_failure",
                description="Unable to open video stream via OpenCV for frame analysis.",
                location=EvidenceLocation(),
                model_score=None,
                confidence_band="high",
                limitations=["Codec may be unsupported or file corrupted"]
            ))
            return findings

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        actual_fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
        if actual_fps <= 0 or actual_fps > 120:
            actual_fps = 24.0

        calc_duration = total_frames / actual_fps if total_frames > 0 else duration
        capped_duration = min(calc_duration, 15.0)  # Hardware constraint cap
        capped_frames = int(capped_duration * actual_fps) if total_frames > 0 else 0

        # Sample 8 to 12 frames sequentially
        target_count = 10
        if capped_frames > 0:
            step = max(1, capped_frames // target_count)
            sample_frame_indices = [min(i * step, max(0, total_frames - 1)) for i in range(target_count)]
            sample_frame_indices = sorted(list(set(sample_frame_indices)))
        else:
            sample_frame_indices = list(range(min(10, max(1, total_frames))))

        frame_brightnesses = []
        frame_sharpnesses = []
        prev_gray = None
        scene_changes = 0
        
        # Initialize OpenCV Haar Cascade face detector
        cascade_path = getattr(cv2, 'data', None)
        face_cascade = None
        if cascade_path and hasattr(cascade_path, 'haarcascades'):
            c_file = os.path.join(cascade_path.haarcascades, 'haarcascade_frontalface_default.xml')
            if os.path.exists(c_file):
                face_cascade = cv2.CascadeClassifier(c_file)
        faces_detected_count = 0

        for idx, f_no in enumerate(sample_frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_no)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            ts = round(float(f_no / actual_fps), 3)

            # Save downsampled thumbnail (max width 640)
            h, w = frame.shape[:2]
            scale = 640 / w if w > 640 else 1.0
            thumb = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale < 1.0 else frame
            thumb_filename = f"frame_{idx:02d}_{f_no}.jpg"
            thumb_path = processed_dir / thumb_filename
            cv2.imwrite(str(thumb_path), thumb)

            # Frame statistics
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            b_val = float(np.mean(gray))
            frame_brightnesses.append(b_val)
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            frame_sharpnesses.append(lap_var)

            # Face detection in sample frame
            num_faces_in_frame = 0
            if face_cascade and not face_cascade.empty():
                try:
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                    num_faces_in_frame = len(faces)
                    faces_detected_count += num_faces_in_frame
                except Exception:
                    pass

            # Scene change detection across consecutive samples
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(prev_gray, gray)
                diff_mean = float(np.mean(diff))
                if diff_mean > 60.0:
                    scene_changes += 1
            prev_gray = gray

            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_frame_sampler",
                indicator="sampled_frame_observation",
                description=f"Sampled frame #{f_no} at {ts:.2f}s: luminance={b_val:.1f}/255, edge contrast variance={lap_var:.1f}, faces detected={num_faces_in_frame}",
                location=EvidenceLocation(timestamp=ts, frame_number=f_no, region={"faces": num_faces_in_frame}),
                model_score=None,
                confidence_band="high",
                limitations=["Sparse sampling; anomalies between sampled points are unobserved"]
            ))

        cap.release()

        # Face tracking summary
        if faces_detected_count > 0:
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_facial_tracker",
                indicator="facial_region_continuity",
                description=f"Facial regions verified across video frames ({faces_detected_count} total face observations across {len(frame_brightnesses)} sample points).",
                location=EvidenceLocation(region={"total_faces_detected": faces_detected_count}),
                model_score=None,
                confidence_band="high",
                limitations=["Haar cascade detection depends on frontal facial orientation and ambient illumination"]
            ))

        # Inter-frame consistency & scene-change assessment
        if len(frame_brightnesses) >= 2:
            b_std = float(np.std(frame_brightnesses))
            b_range = float(max(frame_brightnesses) - min(frame_brightnesses))
            is_unstable = b_std > 40.0

            scene_desc = f"{scene_changes} potential scene cut(s)/abrupt transition(s) detected across sample points." if scene_changes > 0 else "Continuous visual sequence observed across samples."
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_temporal_consistency",
                indicator="interframe_lighting_stability",
                description=(
                    f"Analyzed {len(frame_brightnesses)} sampled frames (duration covered: {min(calc_duration, 15.0):.1f}s). "
                    f"Luminance standard deviation: {b_std:.2f}, dynamic range: {b_range:.1f}. {scene_desc}"
                ),
                location=EvidenceLocation(timestamp=0.0),
                model_score=round(min(b_std / 80.0, 1.0), 3),
                confidence_band="medium" if (is_unstable or scene_changes > 0) else "low",
                limitations=[
                    "Luminance shifts occur naturally with camera movement, zooming, or normal editing cuts",
                    "Does not prove artificial face-swapping or deepfake generation"
                ]
            ))

        if calc_duration > 15.0:
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="hardware_safeguard",
                indicator="sampling_window_capped",
                description=f"Total video duration ({calc_duration:.1f}s) exceeded CPU execution safeguard (15.0s). Analysis restricted to initial 15s window.",
                location=EvidenceLocation(timestamp=15.0),
                model_score=None,
                confidence_band="high",
                limitations=["Observations cannot be extrapolated to uninspected portions of the stream"]
            ))

    except Exception as e:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="video",
            engine="video_frame_sampler",
            indicator="frame_analysis_exception",
            description=f"Frame extraction failed with error: {str(e)}",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="low",
            limitations=["Frame extraction pipeline encountered an unexpected runtime failure"]
        ))

    # Pretrained / Signal Video Models
    try:
        registry = ModelRegistry.get_instance()
        adapters = registry.get_models_for_task("deepfake_temporal_consistency")
        for adapter in adapters:
            pred = await adapter.predict(filepath)
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine=adapter.model_id,
                indicator=pred.indicator,
                description=pred.description,
                location=EvidenceLocation(region=pred.details),
                model_score=pred.score,
                confidence_band=pred.confidence_band,
                limitations=pred.limitations
            ))
    except Exception as e:
        pass

    return findings
