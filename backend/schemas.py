from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any

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
    confidence_band: str = "medium"  # "high", "medium", "low"
    limitations: list[str] = Field(default_factory=list)

class CorrelationResult(BaseModel):
    correlation_id: str
    source_finding_id: str
    target_finding_id: str
    source_evidence_id: str | None = None
    target_evidence_id: str | None = None
    relationship_type: str  # SUPPORTS, CONTRADICTS, RELATED, TIME_ALIGNED, SAME_CONTENT_CANDIDATE
    explanation: str
    strength: float
    rule_id: str = ""
    limitations: list[str] = Field(default_factory=list)

class InvestigationCreate(BaseModel):
    title: str
    description: str = ""
    reference_context: str = ""
    structured_facts: dict[str, Any] = Field(default_factory=dict)
    ai_enabled: bool = False
    ai_provider: str = "gemini"

class InvestigationResponse(BaseModel):
    id: str
    title: str
    description: str
    reference_context: str
    structured_facts: dict[str, Any] = Field(default_factory=dict)
    ai_enabled: bool = False
    ai_provider: str = "gemini"
    status: str
    created_at: datetime
    evidence_count: int = 0
    analysis_count: int = 0
    findings_count: int = 0
    correlations_count: int = 0
    last_analyzed_at: datetime | None = None

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
    source_evidence_id: str | None = None
    target_evidence_id: str | None = None
    relationship_type: str
    explanation: str
    strength: float
    rule_id: str = ""
    limitations: list[str] = []

class DashboardStatsResponse(BaseModel):
    total_investigations: int
    total_evidence: int
    completed_analyses: int
    pending_analyses: int
    failed_analyses: int
    total_findings: int
    total_correlations: int
    pipeline_status: dict[str, int]

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime

class AIProviderConfigResponse(BaseModel):
    id: str
    provider_name: str
    has_key: bool
    masked_key: str
    is_enabled: bool
    selected_model: str
    connection_status: str
    last_tested_at: datetime | None = None
    last_error: str | None = None
    available_models: list[str] = Field(default_factory=list)
    config_source: str = "backend/.env"
    execution_mode: str = "HYBRID"

class AIProviderUpdateRequest(BaseModel):
    api_key: str | None = None
    is_enabled: bool | None = None
    selected_model: str | None = None

class AIProviderTestResponse(BaseModel):
    provider: str
    success: bool
    status: str
    message: str
    model_used: str | None = None

class ReferenceExtractionRequest(BaseModel):
    text: str

class ReferenceExtractionResponse(BaseModel):
    event_date: str = ""
    event_time: str = ""
    location: str = ""
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    event_type: str = ""
    important_claims: list[str] = Field(default_factory=list)

class ReportResponse(BaseModel):
    investigation: dict
    evidence_items: list[dict]
    findings: list[dict]
    correlations: list[dict]
    assessment: dict = Field(default_factory=dict)
    summary: dict
    limitations: list[str]
    generated_at: datetime
