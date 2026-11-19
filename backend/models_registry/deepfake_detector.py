import cv2
import numpy as np
from typing import Optional, Any
from backend.models_registry.base_adapter import BaseModelAdapter, ModelPrediction

class VideoTemporalConsistencyDetector(BaseModelAdapter):
    """
    Analyzes temporal consistency across extracted sequential video frames.
    Deepfakes and frame-interpolated/face-swapped videos frequently exhibit
    high-frequency inter-frame flicker, color distribution jitter, or boundary discontinuities.
    """
    def __init__(self):
        super().__init__(
            model_id="temporal_consistency_detector",
            version="1.0.1",
            detection_task="deepfake_temporal_consistency",
            provider="TruthLens-VideoForensics"
        )

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        try:
            cap = cv2.VideoCapture(evidence_path)
            if not cap.isOpened():
                return ModelPrediction(
                    model_id=self.model_id,
                    version=self.version,
                    detection_task=self.detection_task,
                    score=None,
                    confidence_band="low",
                    indicator="video_read_failure",
                    description="Failed to open video container for temporal analysis.",
                    limitations=["Corrupted or unsupported video stream"]
                )

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames < 4:
                cap.release()
                return ModelPrediction(
                    model_id=self.model_id,
                    version=self.version,
                    detection_task=self.detection_task,
                    score=None,
                    confidence_band="low",
                    indicator="video_too_short",
                    description="Insufficient frames (<4) for temporal jitter analysis.",
                    limitations=["Video must contain multiple frames for inter-frame temporal assessment"]
                )

            # Sample 10 frames evenly across the video
            sample_indices = np.linspace(0, max(0, total_frames - 1), min(10, total_frames), dtype=int)
            prev_gray = None
            diff_scores = []

            for idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if not ret:
                    continue

                # Resize to small dimensions for fast CPU evaluation
                small = cv2.resize(frame, (160, 120))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                if prev_gray is not None:
                    # Normalized absolute difference between consecutive sample frames
                    frame_diff = np.mean(np.abs(gray.astype(float) - prev_gray.astype(float)))
                    diff_scores.append(float(frame_diff))

                prev_gray = gray

            cap.release()

            if not diff_scores:
                return ModelPrediction(
                    model_id=self.model_id,
                    version=self.version,
                    detection_task=self.detection_task,
                    score=None,
                    confidence_band="low",
                    indicator="insufficient_sample_frames",
                    description="Could not extract enough valid frames for temporal evaluation.",
                    limitations=["Video decoding failure during sampling"]
                )

            # Analyze variance of frame differences (high spike variance = flicker/jitter)
            mean_diff = float(np.mean(diff_scores))
            std_diff = float(np.std(diff_scores))
            jitter_ratio = (std_diff / (mean_diff + 1e-5))

            score = round(float(np.clip(jitter_ratio / 2.5, 0.0, 1.0)), 3)
            band = "low" if score < 0.4 else ("medium" if score < 0.75 else "high")

            desc = (
                f"Temporal inter-frame consistency evaluated across {len(diff_scores) + 1} sample frames "
                f"(Mean difference: {mean_diff:.1f}, Jitter ratio: {jitter_ratio:.2f}). "
                f"{'Elevated frame-to-frame variance detected, which may indicate splicing, rapid cuts, or face-replacement flicker.' if jitter_ratio > 1.2 else 'Consistent temporal continuity across sample frames.'}"
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=score,
                confidence_band=band,
                indicator="temporal_consistency_score",
                description=desc,
                details={
                    "sample_frames_analyzed": len(diff_scores) + 1,
                    "mean_frame_difference": round(mean_diff, 2),
                    "jitter_ratio": round(jitter_ratio, 3)
                },
                limitations=[
                    "High motion scenes, hand-held camera shake, or abrupt video cuts naturally elevate jitter metrics",
                    "Compression bit-rate drops can create temporal macroblocking artifacts",
                    "Score is a heuristic indicator and must not be used as sole proof of facial alteration"
                ]
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="temporal_analysis_exception",
                description=f"Temporal analysis error: {str(e)}",
                limitations=["Failure during video frame differential extraction"]
            )
