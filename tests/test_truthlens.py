import os
import sys
import asyncio
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.forensic.hashing import compute_sha256
from backend.forensic.metadata import extract_image_metadata, extract_video_metadata, extract_audio_metadata
from backend.engines.image_engine import analyze_image
from backend.engines.video_engine import analyze_video
from backend.engines.audio_engine import analyze_audio
from backend.engines.text_engine import analyze_text
from backend.correlation.correlator import correlate_findings
from backend.correlation.rules import apply_all_rules
from backend.schemas import Finding, EvidenceLocation
from backend.forensic.report_generator import generate_pdf_report
from backend.database import init_db, SessionLocal
from backend.models import Investigation, Evidence, AnalysisRun, FindingRecord, Correlation

class TruthLensCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.sample_dir = Path("sample_data")

    def test_01_sha256_computation(self):
        img_path = self.sample_dir / "sample_image.jpg"
        hash_val = compute_sha256(img_path)
        self.assertEqual(len(hash_val), 64)
        # Verify deterministic hash
        hash_val_2 = compute_sha256(img_path)
        self.assertEqual(hash_val, hash_val_2)

    def test_02_image_engine_and_ela(self):
        img_path = str(self.sample_dir / "sample_image.jpg")
        findings = asyncio.run(analyze_image("test_img_ev", img_path, "image"))
        self.assertGreater(len(findings), 0)
        
        # Verify common schema compliance
        for f in findings:
            self.assertIsInstance(f, Finding)
            self.assertIn(f.confidence_band, ["high", "medium", "low"])
            self.assertIsInstance(f.limitations, list)
            
        indicators = [f.indicator for f in findings]
        self.assertIn("file_properties", indicators)
        self.assertIn("compression_error_distribution", indicators)
        
        # Check ELA visualization exists
        ela_viz = Path(f"storage/processed/test_img_ev/ela_visualization.png")
        self.assertTrue(ela_viz.exists())

    def test_03_video_engine_frame_sampling(self):
        vid_path = str(self.sample_dir / "sample_video.mp4")
        findings = asyncio.run(analyze_video("test_vid_ev", vid_path, "video"))
        self.assertGreater(len(findings), 0)
        
        frame_obs = [f for f in findings if f.indicator == "sampled_frame_observation"]
        self.assertGreater(len(frame_obs), 0)
        # Verify timestamps are populated
        self.assertIsNotNone(frame_obs[0].location.timestamp)

    def test_04_audio_engine_features_and_visuals(self):
        aud_path = str(self.sample_dir / "sample_audio.wav")
        findings = asyncio.run(analyze_audio("test_aud_ev", aud_path, "audio"))
        self.assertGreater(len(findings), 0)
        
        waveform_path = Path("storage/processed/test_aud_ev/waveform.png")
        spectrogram_path = Path("storage/processed/test_aud_ev/spectrogram.png")
        self.assertTrue(waveform_path.exists())
        self.assertTrue(spectrogram_path.exists())

    def test_05_text_engine_contradiction_detection(self):
        text_path = str(self.sample_dir / "transcript_contradiction.txt")
        reference_context = "The executive conference occurred in Bangalore on Monday with delegates."
        findings = asyncio.run(analyze_text("test_txt_ev", text_path, "text", reference_context))
        
        indicators = [f.indicator for f in findings]
        self.assertIn("location_mismatch_detected", indicators)
        
        mismatch_finding = next(f for f in findings if f.indicator == "location_mismatch_detected")
        self.assertIn("Chennai", mismatch_finding.description)
        self.assertIn("Bangalore", mismatch_finding.description)
        # Crucial principle: limitations stated
        self.assertGreater(len(mismatch_finding.limitations), 0)

    def test_06_cross_modal_correlation_rules(self):
        # Create controlled findings to test correlation
        f1 = Finding(
            finding_id="f1",
            evidence_id="ev_img",
            media_type="image",
            engine="metadata_extraction",
            indicator="metadata_timestamp",
            description="Embedded timestamp (DateTimeOriginal): 2026-05-18",
            location=EvidenceLocation(),
            confidence_band="high",
            limitations=["EXIF reported date"]
        )
        f2 = Finding(
            finding_id="f2",
            evidence_id="ev_txt",
            media_type="text",
            engine="entity_extractor",
            indicator="extracted_entities",
            description="Extracted entities: Temporal/Dates: 2026-11-20; Locations: Bangalore",
            location=EvidenceLocation(),
            confidence_band="medium",
            limitations=["Pattern matched"]
        )
        f3 = Finding(
            finding_id="f3",
            evidence_id="ev_aud",
            media_type="audio",
            engine="audio_spectral_acoustic",
            indicator="acoustic_profile",
            description="Audio recorded in Bangalore headquarters during meeting session.",
            location=EvidenceLocation(timestamp=1.2),
            confidence_band="medium",
            limitations=["Acoustic observation"]
        )
        f4 = Finding(
            finding_id="f4",
            evidence_id="ev_vid",
            media_type="video",
            engine="video_frame_sampler",
            indicator="sampled_frame_observation",
            description="Video frame sampled during meeting session in Bangalore.",
            location=EvidenceLocation(timestamp=1.0),
            confidence_band="high",
            limitations=["Sampled observation"]
        )

        all_f = [f1, f2, f3, f4]
        correlations = asyncio.run(correlate_findings(all_f))
        
        self.assertGreater(len(correlations), 0)
        types = set(c.relationship_type for c in correlations)
        # We expect CONTRADICTS (date conflict), TIME_ALIGNED (audio/video ~1.0s vs 1.2s), RELATED (shared Bangalore)
        self.assertTrue(len(types.intersection({"CONTRADICTS", "TIME_ALIGNED", "RELATED"})) >= 2)
        
        for c in correlations:
            self.assertIsNotNone(c.explanation)
            self.assertGreater(len(c.rule_id), 0)
            self.assertGreaterEqual(c.strength, 0.0)
            self.assertLessEqual(c.strength, 1.0)

    def test_07_pdf_report_generation(self):
        report_data = {
            "investigation": {
                "id": "inv_test_uuid",
                "title": "Operation Verified Truth",
                "description": "Multi-modal digital forensics assessment.",
                "reference_context": "The conference occurred in Bangalore on Monday.",
                "status": "completed",
            },
            "evidence_items": [
                {
                    "original_filename": "sample_image.jpg",
                    "media_type": "image",
                    "file_size": 154200,
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                }
            ],
            "findings": [
                {
                    "engine": "ela_engine",
                    "indicator": "compression_error_distribution",
                    "description": "Error Level Analysis indicates uniform compression.",
                    "confidence_band": "low",
                    "model_score": 0.35,
                    "limitations": ["ELA is a heuristic tool, not definitive proof of tampering"]
                }
            ],
            "correlations": [
                {
                    "relationship_type": "RELATED",
                    "explanation": "Image and transcript corroborate location.",
                    "strength": 0.85,
                    "rule_id": "RULE_LOCATION_MATCH"
                }
            ],
            "summary": {
                "total_evidence": 1,
                "total_findings": 1,
                "total_correlations": 1,
                "confidence_distribution": {"low": 1}
            },
            "limitations": ["Requires qualified analyst human review"]
        }
        
        pdf_path = generate_pdf_report(report_data)
        self.assertTrue(pdf_path.exists())
        self.assertGreater(os.path.getsize(pdf_path), 1000)

    def test_08_fault_isolation(self):
        """Verify that an intentional failure in one engine does not kill the entire investigation."""
        # Pass an unreadable/corrupt path to image engine
        corrupted_path = "non_existent_file.jpg"
        findings = asyncio.run(analyze_image("ev_fail", corrupted_path, "image"))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].indicator, "file_read_error")

if __name__ == '__main__':
    unittest.main()
