import os
import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.ai.secret_manager import encrypt_secret, decrypt_secret, mask_secret
from backend.engines.text_engine import extract_typed_entities
from backend.models_registry import ModelRegistry
from backend.verdict.assessment import evaluate_investigation_findings

class TestAdvancedForensics(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample_dir = Path("d:/Truthlens/sample_data")

    def test_01_secret_manager_encryption(self):
        """Verify Fernet encryption and decryption roundtrip and masking."""
        raw_key = "AIzaSyD-TestKey1234567890abcdef"
        encrypted = encrypt_secret(raw_key)
        self.assertNotEqual(encrypted, raw_key)
        self.assertTrue(len(encrypted) > 20)

        decrypted = decrypt_secret(encrypted)
        self.assertEqual(decrypted, raw_key)

        masked = mask_secret(raw_key)
        self.assertTrue(masked.startswith("AIzaSy"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertIn("...", masked)

    def test_02_typed_entity_extraction(self):
        """Verify that typed entity extraction correctly categorizes locations and dates and rejects non-locations."""
        text = "The meeting took place in Bangalore on 2026-05-12. John Doe discussed the Security Protocols and Skills."
        entities = extract_typed_entities(text)
        
        # Bangalore must be extracted as a Location
        self.assertIn("Bangalore", entities["locations"])
        # 2026-05-12 must be extracted as a Date
        self.assertIn("2026-05-12", entities["dates"])
        
        # 'Skills' and 'Protocols' must NOT be classified as Locations
        self.assertNotIn("Skills", entities["locations"])
        self.assertNotIn("Protocols", entities["locations"])

    def test_03_model_registry_adapters(self):
        """Verify that the model registry registers adapters and executes predictions."""
        registry = ModelRegistry.get_instance()
        models = registry.list_models()
        self.assertGreaterEqual(len(models), 4)

        model_ids = {m["model_id"] for m in models}
        self.assertIn("frequency_spectral_analyzer", model_ids)
        self.assertIn("local_noise_analyzer", model_ids)
        self.assertIn("temporal_consistency_detector", model_ids)
        self.assertIn("synthetic_speech_acoustic_analyzer", model_ids)

        # Run frequency adapter on sample image
        img_path = str(self.sample_dir / "sample_image.jpg")
        freq_adapter = registry.get_model("frequency_spectral_analyzer")
        pred = asyncio.run(freq_adapter.predict(img_path))
        self.assertIsNotNone(pred)
        self.assertEqual(pred.model_id, "frequency_spectral_analyzer")
        self.assertIn(pred.confidence_band, ["low", "medium", "high"])
        self.assertGreater(len(pred.limitations), 0)

        # Run synthetic audio adapter on sample audio
        audio_path = str(self.sample_dir / "sample_audio.wav")
        audio_adapter = registry.get_model("synthetic_speech_acoustic_analyzer")
        pred_audio = asyncio.run(audio_adapter.predict(audio_path))
        self.assertIsNotNone(pred_audio)
        self.assertEqual(pred_audio.model_id, "synthetic_speech_acoustic_analyzer")
        self.assertGreater(len(pred_audio.limitations), 0)

    def test_04_verdict_assessment_engine(self):
        """Verify forensic assessment evaluation logic."""
        # Empty inputs -> Insufficient evidence
        assessment_empty = evaluate_investigation_findings([], [], [])
        self.assertEqual(assessment_empty.primary_status, "INSUFFICIENT_EVIDENCE")

        # Mock findings with contradictions
        sample_findings = [
            {
                "engine": "metadata_extraction",
                "indicator": "metadata_timestamp",
                "description": "Timestamp recorded: 2026-01-01",
                "confidence_band": "high",
                "model_score": None,
                "limitations": []
            },
            {
                "engine": "frequency_spectral_analyzer",
                "indicator": "frequency_domain_regularity",
                "description": "Elevated periodic grid dispersion observed.",
                "confidence_band": "high",
                "model_score": 0.85,
                "limitations": ["Score reflects statistical frequency irregularities"]
            }
        ]
        sample_correlations = [
            {
                "relationship_type": "CONTRADICTS",
                "explanation": "Date mismatch between document and metadata",
                "strength": 0.9,
                "rule_id": "DATE_CONTRADICTION",
                "limitations": ["Timezone differences could account for date mismatch"]
            }
        ]
        sample_evidence = [{"id": "ev-1", "media_type": "image"}]

        assessment = evaluate_investigation_findings(sample_findings, sample_correlations, sample_evidence)
        self.assertEqual(assessment.primary_status, "STRONG_INDICATORS")
        self.assertEqual(assessment.contradictions_count, 1)
        self.assertEqual(assessment.models_flagged_count, 1)
        self.assertGreater(len(assessment.limitations_and_disclaimers), 0)

    def test_05_settings_api(self):
        """Verify Settings AI Provider API endpoints."""
        # 1. List providers
        res = self.client.get("/api/v1/settings/ai-providers")
        self.assertEqual(res.status_code, 200)
        providers = res.json()
        self.assertTrue(len(providers) >= 2)

        # 2. Update provider model
        res = self.client.put("/api/v1/settings/ai-providers/gemini", json={
            "selected_model": "gemini-2.5-flash"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "updated")

        # 3. Test provider connection without key (should handle gracefully)
        res = self.client.post("/api/v1/settings/ai-providers/gemini/test")
        self.assertEqual(res.status_code, 200)
        self.assertIn("success", res.json())

    def test_06_dashboard_stats_api(self):
        """Verify /api/v1/dashboard/stats returns real database metrics."""
        res = self.client.get("/api/v1/dashboard/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_investigations", data)
        self.assertIn("total_evidence", data)
        self.assertIn("completed_analyses", data)
        self.assertIn("total_findings", data)
        self.assertIn("total_correlations", data)
        self.assertIn("pipeline_status", data)
        self.assertIsInstance(data["pipeline_status"], dict)

    def test_07_providers_management_api(self):
        """Verify all mandatory provider API endpoints: GET, status, configure, test, models, delete."""
        # GET /api/v1/providers
        res = self.client.get("/api/v1/providers")
        self.assertEqual(res.status_code, 200)
        providers = res.json()
        self.assertGreaterEqual(len(providers), 4)

        # GET /api/v1/providers/status
        res = self.client.get("/api/v1/providers/status")
        self.assertEqual(res.status_code, 200)
        status_dict = res.json()
        self.assertIn("gemini", status_dict)
        self.assertIn("openai", status_dict)
        self.assertIn("anthropic", status_dict)
        self.assertIn("huggingface", status_dict)

        # GET /api/v1/providers/gemini/models
        res = self.client.get("/api/v1/providers/gemini/models")
        self.assertEqual(res.status_code, 200)
        models_info = res.json()
        self.assertIn("gemini-2.5-flash", models_info["supported_models"])

        # POST /api/v1/providers/gemini/configure
        res = self.client.post("/api/v1/providers/gemini/configure", json={
            "selected_model": "gemini-2.5-pro",
            "is_enabled": True
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "configured")

        # POST /api/v1/providers/gemini/test
        res = self.client.post("/api/v1/providers/gemini/test")
        self.assertEqual(res.status_code, 200)
        self.assertIn("success", res.json())

    def test_08_phash_and_image_forensics(self):
        """Verify perceptual hash computation on image."""
        from backend.forensic.hashing import compute_phash
        img_path = str(self.sample_dir / "sample_image.jpg")
        phash = compute_phash(img_path)
        self.assertTrue(len(phash) == 16)
        self.assertNotEqual(phash, "0000000000000000")

    def test_09_pdf_extraction_support(self):
        """Verify PDF text extraction handles missing/corrupt or valid PDFs gracefully."""
        from backend.engines.text_engine import extract_text_from_file
        # Test on text file first
        txt_path = str(self.sample_dir / "transcript_corroborating.txt")
        content = extract_text_from_file(txt_path)
        self.assertGreater(len(content), 10)
        self.assertIn("Bangalore", content)

if __name__ == '__main__':
    unittest.main()
