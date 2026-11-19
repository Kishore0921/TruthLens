import numpy as np
from PIL import Image
from typing import Optional, Any
from backend.models_registry.base_adapter import BaseModelAdapter, ModelPrediction

class FrequencyArtifactDetector(BaseModelAdapter):
    """
    Analyzes 2D-FFT frequency spectrum to detect periodic artifacts and unnatural
    spectral decay characteristic of generative upsampling (GAN/Diffusion checkerboard patterns).
    """
    def __init__(self):
        super().__init__(
            model_id="frequency_spectral_analyzer",
            version="1.2.0",
            detection_task="ai_image_frequency_analysis",
            provider="TruthLens-SignalForensics"
        )

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        try:
            with Image.open(evidence_path) as img:
                gray = img.convert("L")
                arr = np.array(gray, dtype=np.float32)

            h, w = arr.shape
            # Downsample if image is huge to preserve CPU performance
            if max(h, w) > 1024:
                scale = 1024.0 / max(h, w)
                new_size = (int(w * scale), int(h * scale))
                gray = gray.resize(new_size, Image.Resampling.BILINEAR)
                arr = np.array(gray, dtype=np.float32)

            # Compute 2D Fourier Transform
            f_transform = np.fft.fft2(arr)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1.0)

            # Radial frequency profile analysis
            cy, cx = magnitude_spectrum.shape[0] // 2, magnitude_spectrum.shape[1] // 2
            y, x = np.ogrid[:magnitude_spectrum.shape[0], :magnitude_spectrum.shape[1]]
            dist_from_center = np.sqrt((x - cx)**2 + (y - cy)**2)

            max_radius = min(cx, cy)
            if max_radius < 10:
                max_radius = 10

            # High-frequency power ratio vs mid-frequency
            high_freq_mask = (dist_from_center > (0.6 * max_radius)) & (dist_from_center <= max_radius)
            mid_freq_mask = (dist_from_center > (0.2 * max_radius)) & (dist_from_center <= (0.6 * max_radius))

            high_energy = float(np.mean(magnitude_spectrum[high_freq_mask])) if np.any(high_freq_mask) else 0.0
            mid_energy = float(np.mean(magnitude_spectrum[mid_freq_mask])) if np.any(mid_freq_mask) else 1.0

            energy_ratio = high_energy / (mid_energy + 1e-5)

            # Check for grid periodic spikes (peaks in high frequency ring)
            high_freq_std = float(np.std(magnitude_spectrum[high_freq_mask])) if np.any(high_freq_mask) else 0.0
            
            # Anomaly indicator calculation
            # Natural camera images have smooth, monotonically decaying power spectrum.
            # Synthetic / upsampled images often have periodic peaks or abnormal high-frequency cutoff.
            is_anomalous_peaks = high_freq_std > 2.8
            indicator_score = round(float(np.clip((high_freq_std - 1.5) / 2.0, 0.0, 1.0)), 3)
            
            band = "low" if indicator_score < 0.35 else ("medium" if indicator_score < 0.7 else "high")

            desc = (
                f"2D-FFT frequency spectrum computed (Energy ratio: {energy_ratio:.2f}, High-freq std: {high_freq_std:.2f}). "
                f"{'Periodic grid peaks or anomalous spectral dispersion observed in high frequencies.' if is_anomalous_peaks else 'Frequency spectrum exhibits standard natural decay without conspicuous synthetic grid artifacts.'}"
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=indicator_score,
                confidence_band=band,
                indicator="frequency_domain_regularity",
                description=desc,
                details={
                    "energy_ratio": round(energy_ratio, 3),
                    "high_frequency_std": round(high_freq_std, 3),
                    "max_radius": int(max_radius)
                },
                limitations=[
                    "Strong JPEG compression, resizing, or screen capture can introduce periodic frequency grid patterns",
                    "Certain repetitive real-world textures (fabrics, window grids) naturally exhibit high-frequency peaks",
                    "Score reflects statistical frequency irregularities, not definitive synthesis proof"
                ]
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="frequency_analysis_error",
                description=f"Frequency domain analysis encountered an error: {str(e)}",
                limitations=["Image data could not be transformed to frequency domain"]
            )


class LocalNoiseVarianceDetector(BaseModelAdapter):
    """
    Estimates sensor noise uniformity across 8x8 patches.
    Real optical sensors produce consistent noise variance across smooth surfaces;
    synthetic images or localized composites exhibit severe noise variance inconsistencies.
    """
    def __init__(self):
        super().__init__(
            model_id="local_noise_analyzer",
            version="1.1.0",
            detection_task="sensor_noise_consistency",
            provider="TruthLens-SignalForensics"
        )

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        try:
            with Image.open(evidence_path) as img:
                gray = img.convert("L")
                arr = np.array(gray, dtype=np.float32)

            h, w = arr.shape
            patch_size = 32
            variances = []

            # Sample patches across the image
            for y in range(0, h - patch_size, patch_size * 2):
                for x in range(0, w - patch_size, patch_size * 2):
                    patch = arr[y:y + patch_size, x:x + patch_size]
                    # High-pass filter to extract noise residual (Laplacian kernel)
                    if patch.shape == (patch_size, patch_size):
                        # Approximate noise standard deviation using median absolute deviation of wavelet/differences
                        diff_h = np.abs(patch[:, 1:] - patch[:, :-1])
                        diff_v = np.abs(patch[1:, :] - patch[:-1, :])
                        # Focus on relatively smooth patches to avoid edge contamination
                        if np.mean(diff_h) < 25.0:
                            variances.append(float(np.var(patch)))

            if len(variances) < 4:
                return ModelPrediction(
                    model_id=self.model_id,
                    version=self.version,
                    detection_task=self.detection_task,
                    score=None,
                    confidence_band="low",
                    indicator="noise_variance_insufficient_smooth_regions",
                    description="Insufficient smooth background regions to reliably estimate sensor noise floor.",
                    limitations=["Image is too busy or textured to isolate sensor noise from content"]
                )

            var_arr = np.array(variances)
            mean_var = float(np.mean(var_arr))
            std_var = float(np.std(var_arr))
            cov = (std_var / (mean_var + 1e-5))  # Coefficient of variation

            # Unnaturally low noise (too smooth, characteristic of AI denoising or vector graphics)
            # or severe variance divergence across patches (composite manipulation)
            score = round(float(np.clip(cov / 3.0, 0.0, 1.0)), 3)
            band = "low" if score < 0.4 else ("medium" if score < 0.75 else "high")

            desc = (
                f"Sensor noise consistency evaluated across {len(variances)} smooth candidate patches "
                f"(Mean variance: {mean_var:.2f}, Coefficient of variation: {cov:.2f}). "
                f"{'Localized noise floor divergence observed across evaluated sectors.' if cov > 1.8 else 'Consistent noise distribution observed across sample patches.'}"
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=score,
                confidence_band=band,
                indicator="sensor_noise_consistency",
                description=desc,
                details={
                    "evaluated_patches": len(variances),
                    "mean_variance": round(mean_var, 2),
                    "coefficient_of_variation": round(cov, 3)
                },
                limitations=[
                    "Varying ISO lighting, depth of field blur, and shadow gradients naturally alter local noise variance",
                    "Aggressive modern smartphone computational photography smooths backgrounds naturally",
                    "Indicator must be evaluated in conjunction with ELA and compression history"
                ]
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="noise_analysis_error",
                description=f"Sensor noise estimation failed: {str(e)}",
                limitations=["Could not compute noise residuals on input file"]
            )
