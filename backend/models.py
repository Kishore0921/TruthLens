import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    reference_context = Column(Text, default="")
    structured_facts_json = Column(Text, default="{}")
    ai_enabled = Column(Boolean, default=False)
    ai_provider = Column(String, default="gemini")
    status = Column(String, default="created")  # created, analyzing, analyzed, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    evidence_items = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="investigation", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    media_type = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    investigation = relationship("Investigation", back_populates="evidence_items")
    findings = relationship("FindingRecord", back_populates="evidence", cascade="all, delete-orphan")

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    status = Column(String, default="pending")  # PENDING, PROCESSING, COMPLETED, PARTIALLY_COMPLETED, FAILED
    progress_json = Column(Text, default="{}")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    investigation = relationship("Investigation", back_populates="analysis_runs")
    findings = relationship("FindingRecord", back_populates="analysis_run", cascade="all, delete-orphan")
    correlations = relationship("Correlation", back_populates="analysis_run", cascade="all, delete-orphan")

class FindingRecord(Base):
    __tablename__ = "findings"
    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analysis_runs.id"), nullable=False)
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=False)
    engine = Column(String, nullable=False)
    indicator = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location_json = Column(Text, default="{}")
    model_score = Column(Float, nullable=True)
    confidence_band = Column(String, default="medium")
    limitations_json = Column(Text, default="[]")
    
    analysis_run = relationship("AnalysisRun", back_populates="findings")
    evidence = relationship("Evidence", back_populates="findings")

class Correlation(Base):
    __tablename__ = "correlations"
    id = Column(String, primary_key=True, default=gen_uuid)
    analysis_id = Column(String, ForeignKey("analysis_runs.id"), nullable=False)
    source_finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    target_finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    source_evidence_id = Column(String, nullable=True)
    target_evidence_id = Column(String, nullable=True)
    relationship_type = Column(String, nullable=False)  # SUPPORTS, CONTRADICTS, RELATED, TIME_ALIGNED, SAME_CONTENT_CANDIDATE
    explanation = Column(Text, nullable=False)
    strength = Column(Float, default=0.5)
    rule_id = Column(String, default="")
    limitations_json = Column(Text, default="[]")
    
    analysis_run = relationship("AnalysisRun", back_populates="correlations")
    source_finding = relationship("FindingRecord", foreign_keys=[source_finding_id])
    target_finding = relationship("FindingRecord", foreign_keys=[target_finding_id])

class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"
    id = Column(String, primary_key=True)  # "gemini" or "openai"
    provider_name = Column(String, nullable=False)
    encrypted_api_key = Column(Text, default="")
    is_enabled = Column(Boolean, default=True)
    selected_model = Column(String, default="")
    connection_status = Column(String, default="not_configured") # not_configured, configured, connection_successful, connection_failed, rate_limited
    last_tested_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    investigation_id = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    tokens_used = Column(Integer, default=0)
    status = Column(String, default="success")  # success, failed
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
