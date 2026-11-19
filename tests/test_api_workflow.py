import os
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app
from backend.database import init_db

class TestTruthLensAPIWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.sample_dir = Path("sample_data")

    def test_01_health_endpoint(self):
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "1.0.0")

    def test_02_full_multimodal_investigation_workflow(self):
        # 1. Create Investigation
        inv_payload = {
            "title": "Summit Provenance & Speech Analysis",
            "description": "Cross-verifying video broadcast, speech, and field dispatches.",
            "reference_context": "The executive conference occurred in Bangalore on Monday with delegates."
        }
        res = self.client.post("/api/v1/investigations", json=inv_payload)
        self.assertEqual(res.status_code, 201)
        inv = res.json()
        inv_id = inv["id"]
        self.assertEqual(inv["title"], inv_payload["title"])

        # 2. Upload Evidence: Image, Audio, Video, Text
        evidence_files = [
            ("sample_image.jpg", "image/jpeg"),
            ("sample_audio.wav", "audio/wav"),
            ("sample_video.mp4", "video/mp4"),
            ("transcript_contradiction.txt", "text/plain"),
        ]

        uploaded_evidence_ids = []
        for filename, mime in evidence_files:
            file_path = self.sample_dir / filename
            self.assertTrue(file_path.exists(), f"File {file_path} must exist")
            with open(file_path, "rb") as f:
                res = self.client.post(
                    f"/api/v1/investigations/{inv_id}/evidence",
                    files={"file": (filename, f, mime)}
                )
            self.assertEqual(res.status_code, 201, f"Failed uploading {filename}: {res.text}")
            ev_data = res.json()
            self.assertEqual(len(ev_data["sha256"]), 64)
            uploaded_evidence_ids.append(ev_data["id"])

        self.assertEqual(len(uploaded_evidence_ids), 4)

        # 3. Verify Evidence Listing
        res = self.client.get(f"/api/v1/investigations/{inv_id}/evidence")
        self.assertEqual(res.status_code, 200)
        ev_list = res.json()
        self.assertEqual(len(ev_list), 4)

        # 4. Trigger Full Analysis
        res = self.client.post(f"/api/v1/investigations/{inv_id}/analyze")
        self.assertEqual(res.status_code, 200)
        status_data = res.json()
        self.assertIn(status_data["status"], ["completed", "completed_with_errors"])

        # 5. Fetch Findings
        res = self.client.get(f"/api/v1/investigations/{inv_id}/findings")
        self.assertEqual(res.status_code, 200)
        findings = res.json()
        self.assertGreater(len(findings), 0)

        # Verify findings adhere strictly to schema
        for f in findings:
            self.assertIn("engine", f)
            self.assertIn("indicator", f)
            self.assertIn("description", f)
            self.assertIn("confidence_band", f)
            self.assertIn(f["confidence_band"], ["high", "medium", "low"])
            self.assertIsInstance(f["limitations"], list)

        # 6. Fetch Correlations
        res = self.client.get(f"/api/v1/investigations/{inv_id}/correlations")
        self.assertEqual(res.status_code, 200)
        correlations = res.json()
        self.assertGreater(len(correlations), 0)
        
        # Verify valid relationship types
        valid_rel_types = {"SUPPORTS", "CONTRADICTS", "RELATED", "TIME_ALIGNED", "SAME_CONTENT_CANDIDATE"}
        for c in correlations:
            self.assertIn(c["relationship_type"], valid_rel_types)
            self.assertGreater(len(c["explanation"]), 0)
            self.assertGreaterEqual(c["strength"], 0.0)

        # 7. Fetch JSON Report
        res = self.client.get(f"/api/v1/investigations/{inv_id}/report")
        self.assertEqual(res.status_code, 200)
        report = res.json()
        self.assertEqual(report["investigation"]["id"], inv_id)
        self.assertEqual(len(report["evidence_items"]), 4)
        self.assertGreater(len(report["findings"]), 0)

        # 8. Fetch PDF Report
        res = self.client.get(f"/api/v1/investigations/{inv_id}/report/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

        # 9. Verify File Serving Endpoint
        first_ev_id = uploaded_evidence_ids[0]
        res = self.client.get(f"/api/v1/evidence/{first_ev_id}/file")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.content), 0)

if __name__ == '__main__':
    unittest.main()
