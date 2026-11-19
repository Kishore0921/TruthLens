import uuid
import os
import json
import numpy as np
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation
from backend.config import PROCESSED_DIR
from backend.forensic.metadata import extract_video_metadata

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

    # 2. Sequential OpenCV frame extraction (8 - 12 frames, max 15s capped)
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
        extracted_thumbnails = []

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
            extracted_thumbnails.append({"frame_number": f_no, "timestamp": ts, "filename": thumb_filename})

            # Frame statistics
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            b_val = float(np.mean(gray))
            frame_brightnesses.append(b_val)
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            frame_sharpnesses.append(lap_var)

            # Record sample observation
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_frame_sampler",
                indicator="sampled_frame_observation",
                description=f"Sampled frame #{f_no} at {ts}s: luminance={b_val:.1f}/255, edge contrast variance={lap_var:.1f}",
                location=EvidenceLocation(timestamp=ts, frame_number=f_no),
                model_score=None,
                confidence_band="high",
                limitations=["Sparse sampling; inter-frame anomalies may exist between sample points"]
            ))

        cap.release()

        # Inter-frame consistency assessment
        if len(frame_brightnesses) >= 2:
            b_std = float(np.std(frame_brightnesses))
            b_range = float(max(frame_brightnesses) - min(frame_brightnesses))
            sharp_std = float(np.std(frame_sharpnesses))

            # Indicator of lighting stability or sudden scene cuts
            is_unstable = b_std > 40.0
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="video_temporal_consistency",
                indicator="interframe_lighting_stability",
                description=(
                    f"Analyzed {len(frame_brightnesses)} sampled frames (duration covered: {min(calc_duration, 15.0):.1f}s). "
                    f"Luminance standard deviation: {b_std:.2f}, dynamic range: {b_range:.1f}. "
                    f"{'Significant luminance fluctuation detected across samples.' if is_unstable else 'Stable inter-frame illumination.'}"
                ),
                location=EvidenceLocation(timestamp=0.0),
                model_score=round(min(b_std / 80.0, 1.0), 3),
                confidence_band="medium" if is_unstable else "low",
                limitations=[
                    "Luminance variations occur naturally with camera motion, panning, and lighting shifts",
                    "Does not differentiate between benign editing/cuts and deepfake artifacting"
                ]
            ))

        if calc_duration > 15.0:
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                evidence_id=evidence_id,
                media_type="video",
                engine="hardware_safeguard",
                indicator="sampling_window_capped",
                description=f"Total video length ({calc_duration:.1f}s) exceeded CPU execution cap (15.0s). Analysis restricted to initial 15s window.",
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

    return findings
