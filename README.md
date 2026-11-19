# TruthLens 🔍
> **"Detect. Analyze. Correlate. Explain."**

TruthLens is a multimodal digital forensics and deepfake detection web application engineered for hackathons and forensic investigations. It ingests image, video, audio, and text evidence, conducts forensic signal and heuristic analysis on each, correlates observations across media types, and outputs explainable forensic reports with cryptographic chain-of-custody.

---

## 🏛️ Core Forensic Principles

1. **Indicator, Never a Verdict**: A detection score or model metric is an indicator, not a definitive conclusion.
2. **Explainability & Scientific Restraint**:
   - Error Level Analysis (ELA) illustrates compression variance but **cannot independently prove manipulation**.
   - Missing EXIF metadata is standard across web platforms and **cannot prove a file is fake**.
   - Spectral cutoffs in audio can result from telephone filters or lossy codecs (MP3/AAC) and **never prove synthetic voice synthesis**.
3. **Observation Confidence Bands**: Confidence bands describe the empirical reliability of an observation, **never an unsupported probability that a file is fabricated**.
4. **Strict Separation of Findings**: The system explicitly categorizes and visualizes:
   - *Confirmed Metadata* (container headers, cryptographic hashes, dimensions)
   - *Empirical Observations* (luminance statistics, zero-crossing rate, word counts)
   - *Heuristic Indicators* (ELA compression distribution, spectral centroid shifts)
   - *Correlations & Discrepancies* (temporal sync, geographic contradictions)
5. **Mandatory Human Verification**: Every report concludes with an explicit mandate requiring independent human review by qualified analysts.

---

## ⚡ Hardware Constraints & Optimization

TruthLens is purpose-built for commodity resource-constrained hardware (e.g. **Intel Core i5-4310U 2 cores / 4 threads, 8 GB RAM, integrated graphics, no CUDA GPU**):
- **CPU-Only Execution**: Zero heavy PyTorch/TensorFlow weights; zero GPU reliance.
- **Sequential Video Processing**: Videos are capped at a 15-second analysis window with 8–12 sparse frames sampled sequentially to prevent RAM and CPU throttling.
- **Lightweight NLP & Gazetteers**: Deterministic regex gazetteers and morphological rule matching for instant entity extraction without LLM API overhead or gigabyte embeddings.
- **Graceful Degradation**: Every forensic engine functions independently; missing system tools (like `ffprobe`) automatically fall back to OpenCV and signal processing routines without halting the investigation.

---

## 🛠️ Technology Stack

- **Frontend**: React 19, Vite, Tailwind CSS, React Router, Axios, Recharts, `@xyflow/react` (interactive forensic relationship graph), Lucide Icons.
- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, SQLite, Uvicorn.
- **Forensic & Signal Processing**: Pillow, OpenCV (headless), NumPy, SoundFile, Matplotlib (headless Agg backend), Librosa, Hashlib, ReportLab.
- **Architecture**: Single-process lightweight asynchronous web service with zero external cloud dependencies.

---

## 👥 Team Ownership & Module Architecture

| Member | Module | Key Responsibilities & Deliverables |
|---|---|---|
| **Member 1** | **Image & Video Engines** | `backend/engines/image_engine.py`, `backend/engines/video_engine.py`<br>• EXIF/metadata extraction and file property validation<br>• Error Level Analysis (ELA) with Q92 JPEG delta generation & contrast scaling<br>• Video duration capping (15s), OpenCV sequential frame sampling, thumbnail generation, inter-frame luminance variance |
| **Member 2** | **Audio & Text Engines** | `backend/engines/audio_engine.py`, `backend/engines/text_engine.py`<br>• Container properties, waveform and Mel-spectrogram rendering<br>• RMS energy, zero-crossing rate, spectral centroid metrics<br>• Text normalization, entity/date extraction, reference comparison, geographic mismatch detection |
| **Member 3** | **Core Backend & Correlation** | `backend/api/`, `backend/correlation/`, `backend/forensic/`<br>• FastAPI REST API (`/health`, `/investigations`, `/evidence`, `/analyze`, `/report`)<br>• SQLite database schema & SQLAlchemy ORM with foreign keys<br>• Immutable SHA-256 storage (`storage/originals/` and `storage/processed/`)<br>• Cross-modal correlation engine (`backend/correlation/rules.py`) with 5 relationship types<br>• Formal ReportLab PDF generation with human review disclaimers |
| **Member 4** | **Frontend & Visualizations** | `frontend/src/`<br>• Polished dark forensic dashboard (slate/navy theme with cyan/blue accents)<br>• Multi-file drag-and-drop evidence uploader with progress and SHA-256 copy<br>• Evidence inventory, ELA side-by-side viewer, acoustic waveform/spectrogram viewer<br>• Interactive React Flow cross-modal relationship graph with colored edge indicators<br>• Report preview and 1-click PDF download |

---

## 🔬 Cross-Modal Correlation Engine

The central innovation of TruthLens lives in `backend/correlation/`. It bridges distinct evidence types using 5 defined relationship types:

1. **`CONTRADICTS`**: Detected discrepancies between confirmed metadata facts and claims (e.g. an image metadata date conflicting with a transcript stated date, or text reporting "Chennai" while baseline specifies "Bangalore").
2. **`SUPPORTS`**: Corroborating evidence across modalities (e.g. both text and image EXIF confirming identical calendar dates).
3. **`TIME_ALIGNED`**: Temporal synchronization across media (e.g. a video frame sampled at 1.0s aligning with an audio acoustic peak at 1.2s within a 1.5s tolerance).
4. **`RELATED`**: Shared entities, locations, or organizations identified across distinct evidence files.
5. **`SAME_CONTENT_CANDIDATE`**: High vocabulary Jaccard similarity or identical cryptographic hashes indicating candidate duplicates or identical origin.

Every correlation records:
- `correlation_id` (UUID)
- `relationship_type`
- `source_finding_id` & `target_finding_id`
- `strength` (0.0 to 1.0, stored separately from detector confidence)
- `rule_id` (e.g. `RULE_METADATA_DATE_CONFLICT`, `RULE_GEOGRAPHIC_CONTRADICTION`)
- `explanation` (Human-readable rationale)

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.12+ (64-bit)
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Clone and enter the repository
cd TruthLens

# Create and activate Python virtual environment
py -3.12 -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Generate sample test media
python create_samples.py

# Run the test suite
python -m unittest tests/test_truthlens.py
python -m unittest tests/test_api_workflow.py

# Start the FastAPI backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation and Swagger UI will be live at: **http://localhost:8000/docs**

### 2. Frontend Setup
```bash
# In a new terminal window:
cd TruthLens/frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open your browser at: **http://localhost:5173**

---

## 🧪 Verification & Automated Testing

TruthLens includes comprehensive unit and integration test coverage:

```bash
# Execute unit tests for forensic modules, ELA, audio, video, text, rules & PDF
python -m unittest tests/test_truthlens.py

# Execute end-to-end API investigative workflow test
python -m unittest tests/test_api_workflow.py
```

All 10+ core test suites verify:
- ✅ Deterministic SHA-256 calculation
- ✅ EXIF extraction & Pillow Error Level Analysis difference map generation
- ✅ OpenCV sequential frame extraction (sampling 8-12 frames within 15s window)
- ✅ Audio waveform, Mel-spectrogram, RMS energy & spectral centroid calculation
- ✅ Text corpus normalization & location discrepancy detection (Bangalore vs Chennai)
- ✅ Cross-modal correlation rules and relationship generation
- ✅ Fault isolation: an intentional engine failure does not interrupt overall analysis
- ✅ Complete investigative workflow: creation -> upload -> analysis -> graph -> PDF report
