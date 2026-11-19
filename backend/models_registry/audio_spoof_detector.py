import numpy as np
import soundfile as sf
import librosa
from typing import Optional, Any
from backend.models_registry.base_adapter import BaseModelAdapter, ModelPrediction

class SyntheticAudioDetector(BaseModelAdapter):
    """
    Evaluates acoustic characteristics of audio for markers of neural text-to-speech
    and voice conversion (artificial silence, abrupt high-frequency roll-off, spectral flatness anomalies).
    """
    def __init__(self):
        super().__init__(
            model_id="synthetic_speech_acoustic_analyzer",
            version="1.0.2",
            detection_task="synthetic_audio_detection",
            provider="TruthLens-AudioForensics"
        )

    async def predict(self, evidence_path: str, metadata: Optional[dict[str, Any]] = None) -> ModelPrediction:
        try:
            # Load audio using librosa or soundfile (limit to 15s to respect CPU limits)
            y, sr = librosa.load(evidence_path, sr=None, duration=15.0)
            if len(y) == 0:
                return ModelPrediction(
                    model_id=self.model_id,
                    version=self.version,
                    detection_task=self.detection_task,
                    score=None,
                    confidence_band="low",
                    indicator="empty_audio_track",
                    description="Audio file contains no decodable audio samples.",
                    limitations=["Audio track is silent or unreadable"]
                )

            # 1. High-frequency cutoff analysis
            # Most modern neural vocoders (HiFi-GAN, MelGAN) or older TTS models operate at 16kHz or 22.05kHz,
            # exhibiting unnatural dead silence or sharp brick-wall cutoffs above 8kHz or 11kHz.
            spec = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Check energy distribution in highest 15% of spectrum
            high_cutoff_idx = int(len(freqs) * 0.85)
            high_energy = float(np.mean(spec[high_cutoff_idx:, :]))
            total_energy = float(np.mean(spec)) + 1e-6
            high_ratio = high_energy / total_energy

            # 2. Spectral Flatness (noise-like vs tonal)
            flatness = librosa.feature.spectral_flatness(y=y)
            mean_flatness = float(np.mean(flatness))

            # 3. Background silence floor consistency
            # Synthetic speech recordings often possess digital zero (infinite SNR) in pauses between words,
            # whereas physical microphones capture ambient room reverberation/noise floor.
            abs_y = np.abs(y)
            silence_samples = abs_y[abs_y < 0.005]
            silence_ratio = float(len(silence_samples) / (len(abs_y) + 1e-6))
            perfect_zero_ratio = float(np.sum(abs_y < 1e-6) / (len(abs_y) + 1e-6))

            # Synthesize heuristic indicator score
            is_brick_wall = high_ratio < 0.005 and sr > 24000
            is_sterile_silence = perfect_zero_ratio > 0.08

            score_components = []
            if is_brick_wall:
                score_components.append(0.65)
            if is_sterile_silence:
                score_components.append(0.70)
            if mean_flatness < 0.001 or mean_flatness > 0.2:
                score_components.append(0.50)

            score = round(float(np.mean(score_components)), 3) if score_components else 0.15
            band = "low" if score < 0.4 else ("medium" if score < 0.75 else "high")

            reasons = []
            if is_brick_wall:
                reasons.append("Sharp high-frequency spectral attenuation characteristic of neural vocoder downsampling")
            if is_sterile_silence:
                reasons.append("Unnaturally sterile digital zero pauses lacking physical microphone room ambient noise")
            
            reason_str = "; ".join(reasons) if reasons else "Acoustic spectrum and room ambience consistent with natural recording conditions"

            desc = (
                f"Acoustic synthetic speech analysis completed (Sampling rate: {sr} Hz, "
                f"Spectral flatness: {mean_flatness:.5f}, High-band energy ratio: {high_ratio:.4f}). "
                f"Observation: {reason_str}."
            )

            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=score,
                confidence_band=band,
                indicator="acoustic_synthesis_markers",
                description=desc,
                details={
                    "sampling_rate": sr,
                    "mean_spectral_flatness": round(mean_flatness, 6),
                    "high_band_energy_ratio": round(high_ratio, 5),
                    "perfect_zero_ratio": round(perfect_zero_ratio, 4)
                },
                limitations=[
                    "Aggressive digital noise-gate filters or studio post-processing can eliminate ambient noise in legitimate recordings",
                    "Telephony codecs (G.711, AMR) naturally band-limit audio to 3.4kHz or 7kHz",
                    "Acoustic features are indicative heuristics, not conclusive proof of AI voice cloning"
                ]
            )
        except Exception as e:
            return ModelPrediction(
                model_id=self.model_id,
                version=self.version,
                detection_task=self.detection_task,
                score=None,
                confidence_band="low",
                indicator="synthetic_audio_analysis_error",
                description=f"Synthetic audio analysis failed: {str(e)}",
                limitations=["Audio feature computation error"]
            )
