from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class EvidenceLocation(BaseModel):
    timestamp: float | None = None
    frame_number: int | None = None
    region: dict | None = None

class Finding(BaseModel):
    finding_id: str
    evidence_id: str
    media_type: str
    engine: str
    indicator: str
    description: str
    location: EvidenceLocation = Field(default_factory=EvidenceLocation)
    model_score: float | None = None
    confidence_band: str = "medium"
    limitations: list[str] = Field(default_factory=list)

class CorrelationResult(BaseModel):
    correlation_id: str
    source_finding_id: str
    target_finding_id: str
    relationship_type: str
    explanation: str
    strength: float
    rule_id: str = ""

class InvestigationCreate(BaseModel):
    title: str
    description: str = ""
    reference_context: str = ""

class InvestigationResponse(BaseModel):
    id: str
    title: str
    description: str
    reference_context: str
    status: str
    created_at: datetime
    evidence_count: int = 0
    analysis_count: int = 0

class EvidenceResponse(BaseModel):
    id: str
    investigation_id: str
    filename: str
    original_filename: str
    media_type: str
    sha256: str
    file_size: int
    metadata_json: str = "{}"
    created_at: datetime

class AnalysisStatusResponse(BaseModel):
    id: str
    investigation_id: str
    status: str
    progress: dict = {}
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

class FindingResponse(BaseModel):
    id: str
    analysis_id: str
    evidence_id: str
    engine: str
    indicator: str
    description: str
    location: dict = {}
    model_score: float | None = None
    confidence_band: str
    limitations: list[str] = []

class CorrelationResponse(BaseModel):
    id: str
    analysis_id: str
    source_finding_id: str
    target_finding_id: str
    relationship_type: str
    explanation: str
    strength: float
    rule_id: str = ""

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime

class ReportResponse(BaseModel):
    investigation: dict
    evidence_items: list[dict]
    findings: list[dict]
    correlations: list[dict]
    summary: dict
    limitations: list[str]
    generated_at: datetime
