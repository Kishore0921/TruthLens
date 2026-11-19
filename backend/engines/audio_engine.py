import uuid
import os
import numpy as np
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation
from backend.config import PROCESSED_DIR
from backend.forensic.metadata import extract_audio_metadata

async def analyze_audio(evidence_id: str, filepath: str, media_type: str) -> list[Finding]:
    findings: list[Finding] = []
    processed_dir = PROCESSED_DIR / evidence_id
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Metadata
    meta = extract_audio_metadata(filepath)
    duration = float(meta.get("duration", 0.0) or 0.0)
    sample_rate = meta.get("sample_rate", "unknown")
    channels = meta.get("channels", "unknown")
    fmt = meta.get("format", "")
    note = meta.get("note", "")

    file_size = os.path.getsize(filepath)
    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="audio",
        engine="audio_container_info",
        indicator="audio_stream_metadata",
        description=(
            f"Audio stream: {duration:.2f}s duration, {sample_rate} Hz, "
            f"{channels} channel(s), format={fmt or 'native'}, size={file_size:,} bytes. {note}"
        ).strip(),
        location=EvidenceLocation(timestamp=0.0),
        model_score=None,
        confidence_band="high",
        limitations=["Audio container and header properties confirmed from stream inspection"]
    ))

    # 2. Librosa / Soundfile Analysis & Visualizations
    try:
        import matplotlib
        matplotlib.use("Agg")  # Headless non-interactive rendering
        import matplotlib.pyplot as plt
        import librosa

        # Load audio (mono, capped at 60s for performance)
        y, sr = librosa.load(filepath, sr=None, mono=True, duration=60.0)
        actual_len_s = len(y) / sr if sr > 0 else 0.0

        # --- A. Generate Waveform Plot ---
        waveform_path = processed_dir / "waveform.png"
        try:
            fig, ax = plt.subplots(figsize=(8, 2.5), facecolor="#0f172a")
            ax.set_facecolor("#1e293b")
            times = np.linspace(0, actual_len_s, num=len(y))
            # Downsample if very long
            step = max(1, len(y) // 3000)
            ax.plot(times[::step], y[::step], color="#06b6d4", linewidth=0.6, alpha=0.9)
            ax.set_title("Audio Amplitude Waveform", color="#e2e8f0", fontsize=10)
            ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=8)
            ax.set_ylabel("Amplitude", color="#94a3b8", fontsize=8)
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            plt.tight_layout()
            plt.savefig(waveform_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
        except Exception as we:
            print(f"Waveform plot error: {we}")

        # --- B. Generate Mel Spectrogram Plot ---
        spectrogram_path = processed_dir / "spectrogram.png"
        try:
            s = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
            s_db = librosa.power_to_db(s, ref=np.max)

            fig, ax = plt.subplots(figsize=(8, 3.0), facecolor="#0f172a")
            ax.set_facecolor("#1e293b")
            img = ax.imshow(s_db, origin="lower", aspect="auto", cmap="magma",
                            extent=[0, actual_len_s, 0, 8000])
            ax.set_title("Mel Spectrogram (dB)", color="#e2e8f0", fontsize=10)
            ax.set_xlabel("Time (s)", color="#94a3b8", fontsize=8)
            ax.set_ylabel("Frequency (Hz)", color="#94a3b8", fontsize=8)
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            cbar = plt.colorbar(img, ax=ax)
            cbar.ax.yaxis.set_tick_params(color="#94a3b8", labelcolor="#94a3b8")
            plt.tight_layout()
            plt.savefig(spectrogram_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
        except Exception as se:
            print(f"Spectrogram plot error: {se}")

        # --- C. Quantitative Spectral & Acoustic Features ---
        rms = librosa.feature.rms(y=y)[0]
        mean_rms = float(np.mean(rms))
        std_rms = float(np.std(rms))

        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        mean_zcr = float(np.mean(zcr))

        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        mean_centroid = float(np.mean(spectral_centroids))

        # Spectral flatness (measure of noisiness vs harmonic tone)
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        mean_flatness = float(np.mean(flatness))

        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="audio",
            engine="audio_spectral_acoustic",
            indicator="acoustic_profile",
            description=(
                f"Acoustic profile: Mean RMS energy={mean_rms:.4f} (σ={std_rms:.4f}), "
                f"Zero-crossing rate={mean_zcr:.4f}, Spectral centroid={mean_centroid:.1f} Hz, "
                f"Spectral flatness={mean_flatness:.5f}."
            ),
            location=EvidenceLocation(timestamp=0.0),
            model_score=None,
            confidence_band="high",
            limitations=[
                "Descriptive acoustic measurements from signal analysis",
                "Unusual or synthetic-sounding spectral patterns CANNOT independently prove AI voice synthesis or deepfake audio",
                "Compression codecs (MP3/AAC/Opus) introduce severe spectral cutoffs and artifacts resembling synthetic synthesis"
            ]
        ))

        # Check for high frequency cutoff anomalies (often introduced by synthetic models or lossy encoding)
        # We present this as an explainable observation, NEVER a definitive verdict
        cutoff_detected = mean_centroid < 1800 and sr >= 32000
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="audio",
            engine="audio_spectral_acoustic",
            indicator="spectral_frequency_band_distribution",
            description=(
                f"Frequency band concentration: Center of mass at {mean_centroid:.1f} Hz. "
                f"{'Low spectral centroid observed relative to native sampling rate.' if cutoff_detected else 'Spectral distribution conforms to typical voice/acoustic range.'}"
            ),
            location=EvidenceLocation(timestamp=0.0),
            model_score=round(min(mean_centroid / 4000.0, 1.0), 3),
            confidence_band="medium" if cutoff_detected else "low",
            limitations=[
                "Heuristic observation; telephone filters, low-pass filters, and microphone characteristics cause identical cutoffs",
                "Does not prove synthetic speech generation"
            ]
        ))

    except ImportError as ie:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="audio",
            engine="audio_acoustic_fallback",
            indicator="dependency_unavailable",
            description=f"Advanced acoustic library unavailable ({str(ie)}). Falling back to basic container analysis.",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="low",
            limitations=["Signal processing dependencies not fully configured"]
        ))
    except Exception as e:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="audio",
            engine="audio_acoustic_processor",
            indicator="processing_failure",
            description=f"Acoustic feature extraction encountered an issue: {str(e)}",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="low",
            limitations=["Audio analysis pipeline could not parse all frames"]
        ))

    return findings
