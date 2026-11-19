import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Investigation, Evidence, AnalysisRun, FindingRecord, Correlation
from backend.schemas import (
    InvestigationCreate, InvestigationResponse, AnalysisStatusResponse,
    FindingResponse, CorrelationResponse, ReportResponse, DashboardStatsResponse
)
from backend.forensic.report_generator import generate_pdf_report
from backend.verdict.assessment import evaluate_investigation_findings

router = APIRouter(prefix="/api/v1", tags=["investigations"])

@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Retrieve verified aggregated forensic dashboard metrics directly from database."""
    total_inv = db.query(func.count(Investigation.id)).scalar() or 0
    total_ev = db.query(func.count(Evidence.id)).scalar() or 0
    total_findings = db.query(func.count(FindingRecord.id)).scalar() or 0
    total_correlations = db.query(func.count(Correlation.id)).scalar() or 0

    # Analysis runs by status
    completed_runs = db.query(func.count(AnalysisRun.id)).filter(
        AnalysisRun.status.in_(["COMPLETED", "completed", "PARTIALLY_COMPLETED", "completed_with_errors"])
    ).scalar() or 0

    pending_runs = db.query(func.count(AnalysisRun.id)).filter(
        AnalysisRun.status.in_(["PENDING", "pending", "PROCESSING", "running", "analyzing"])
    ).scalar() or 0

    failed_runs = db.query(func.count(AnalysisRun.id)).filter(
        AnalysisRun.status.in_(["FAILED", "failed"])
    ).scalar() or 0

    # Pipeline counts across investigations
    draft_count = db.query(func.count(Investigation.id)).filter(
        Investigation.status.in_(["created", "draft"])
    ).scalar() or 0

    in_analysis_count = db.query(func.count(Investigation.id)).filter(
        Investigation.status.in_(["analyzing", "running"])
    ).scalar() or 0

    analyzed_count = db.query(func.count(Investigation.id)).filter(
        Investigation.status.in_(["analyzed", "completed"])
    ).scalar() or 0

    inv_failed_count = db.query(func.count(Investigation.id)).filter(
        Investigation.status == "failed"
    ).scalar() or 0

    return DashboardStatsResponse(
        total_investigations=total_inv,
        total_evidence=total_ev,
        completed_analyses=completed_runs,
        pending_analyses=pending_runs,
        failed_analyses=failed_runs,
        total_findings=total_findings,
        total_correlations=total_correlations,
        pipeline_status={
            "draft": draft_count,
            "in_analysis": in_analysis_count,
            "analyzed": analyzed_count,
            "failed": inv_failed_count
        }
    )

def _build_investigation_response(inv: Investigation, db: Session) -> InvestigationResponse:
    ev_count = len(inv.evidence_items) if inv.evidence_items else 0
    an_count = len(inv.analysis_runs) if inv.analysis_runs else 0

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.investigation_id == inv.id)
        .order_by(AnalysisRun.started_at.desc())
        .first()
    )

    findings_count = 0
    correlations_count = 0
    last_analyzed = None

    if latest_run:
        findings_count = db.query(func.count(FindingRecord.id)).filter(FindingRecord.analysis_id == latest_run.id).scalar() or 0
        correlations_count = db.query(func.count(Correlation.id)).filter(Correlation.analysis_id == latest_run.id).scalar() or 0
        last_analyzed = latest_run.completed_at or latest_run.started_at

    structured_facts = {}
    try:
        structured_facts = json.loads(inv.structured_facts_json) if inv.structured_facts_json else {}
    except Exception:
        structured_facts = {}

    return InvestigationResponse(
        id=inv.id,
        title=inv.title,
        description=inv.description or "",
        reference_context=inv.reference_context or "",
        structured_facts=structured_facts,
        ai_enabled=bool(inv.ai_enabled),
        ai_provider=inv.ai_provider or "gemini",
        status=inv.status,
        created_at=inv.created_at,
        evidence_count=ev_count,
        analysis_count=an_count,
        findings_count=findings_count,
        correlations_count=correlations_count,
        last_analyzed_at=last_analyzed,
    )

@router.post("/investigations", response_model=InvestigationResponse, status_code=201)
def create_investigation(data: InvestigationCreate, db: Session = Depends(get_db)):
    structured_json = json.dumps(data.structured_facts) if data.structured_facts else "{}"
    inv = Investigation(
        title=data.title,
        description=data.description,
        reference_context=data.reference_context,
        structured_facts_json=structured_json,
        ai_enabled=data.ai_enabled,
        ai_provider=data.ai_provider
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return _build_investigation_response(inv, db)

@router.get("/investigations", response_model=list[InvestigationResponse])
def list_investigations(
    search: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Investigation)
    if status and status.lower() != 'all':
        query = query.filter(Investigation.status == status.lower())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(Investigation.title.ilike(term) | Investigation.description.ilike(term))

    investigations = query.order_by(Investigation.created_at.desc()).all()
    return [_build_investigation_response(inv, db) for inv in investigations]

@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _build_investigation_response(inv, db)

@router.get("/investigations/{investigation_id}/status", response_model=AnalysisStatusResponse)
def get_investigation_status(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.investigation_id == investigation_id)
        .order_by(AnalysisRun.started_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No analysis runs found for this investigation")
    progress = {}
    try:
        progress = json.loads(run.progress_json) if run.progress_json else {}
    except (json.JSONDecodeError, TypeError):
        pass
    return AnalysisStatusResponse(
        id=run.id,
        investigation_id=run.investigation_id,
        status=run.status,
        progress=progress,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )

@router.get("/investigations/{investigation_id}/findings", response_model=list[FindingResponse])
def get_investigation_findings(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.investigation_id == investigation_id)
        .order_by(AnalysisRun.started_at.desc())
        .first()
    )
    if not run:
        return []
    findings = db.query(FindingRecord).filter(FindingRecord.analysis_id == run.id).all()
    results = []
    for f in findings:
        location = {}
        try:
            location = json.loads(f.location_json) if f.location_json else {}
        except (json.JSONDecodeError, TypeError):
            pass
        limitations = []
        try:
            limitations = json.loads(f.limitations_json) if f.limitations_json else []
        except (json.JSONDecodeError, TypeError):
            pass
        results.append(FindingResponse(
            id=f.id,
            analysis_id=f.analysis_id,
            evidence_id=f.evidence_id,
            engine=f.engine,
            indicator=f.indicator,
            description=f.description,
            location=location,
            model_score=f.model_score,
            confidence_band=f.confidence_band,
            limitations=limitations,
        ))
    return results

@router.get("/investigations/{investigation_id}/correlations", response_model=list[CorrelationResponse])
def get_investigation_correlations(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.investigation_id == investigation_id)
        .order_by(AnalysisRun.started_at.desc())
        .first()
    )
    if not run:
        return []
    correlations = db.query(Correlation).filter(Correlation.analysis_id == run.id).all()
    results = []
    for c in correlations:
        lims = []
        try:
            lims = json.loads(c.limitations_json) if c.limitations_json else []
        except Exception:
            lims = []
        results.append(CorrelationResponse(
            id=c.id,
            analysis_id=c.analysis_id,
            source_finding_id=c.source_finding_id,
            target_finding_id=c.target_finding_id,
            source_evidence_id=c.source_evidence_id,
            target_evidence_id=c.target_evidence_id,
            relationship_type=c.relationship_type,
            explanation=c.explanation,
            strength=c.strength,
            rule_id=c.rule_id or "",
            limitations=lims
        ))
    return results

def _build_report_data(inv: Investigation, db: Session) -> dict:
    evidence_items = db.query(Evidence).filter(Evidence.investigation_id == inv.id).all()
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.investigation_id == inv.id)
        .order_by(AnalysisRun.started_at.desc())
        .first()
    )

    findings_list = []
    correlations_list = []
    if run:
        findings = db.query(FindingRecord).filter(FindingRecord.analysis_id == run.id).all()
        for f in findings:
            location = {}
            limitations = []
            try:
                location = json.loads(f.location_json) if f.location_json else {}
            except (json.JSONDecodeError, TypeError):
                pass
            try:
                limitations = json.loads(f.limitations_json) if f.limitations_json else []
            except (json.JSONDecodeError, TypeError):
                pass
            findings_list.append({
                "id": f.id,
                "analysis_id": f.analysis_id,
                "evidence_id": f.evidence_id,
                "engine": f.engine,
                "indicator": f.indicator,
                "description": f.description,
                "location": location,
                "model_score": f.model_score,
                "confidence_band": f.confidence_band,
                "limitations": limitations,
            })

        correlations = db.query(Correlation).filter(Correlation.analysis_id == run.id).all()
        for c in correlations:
            lims = []
            try:
                lims = json.loads(c.limitations_json) if c.limitations_json else []
            except Exception:
                lims = []
            correlations_list.append({
                "id": c.id,
                "analysis_id": c.analysis_id,
                "source_finding_id": c.source_finding_id,
                "target_finding_id": c.target_finding_id,
                "source_evidence_id": c.source_evidence_id,
                "target_evidence_id": c.target_evidence_id,
                "relationship_type": c.relationship_type,
                "explanation": c.explanation,
                "strength": c.strength,
                "rule_id": c.rule_id or "",
                "limitations": lims
            })

    evidence_dicts = [
        {
            "id": e.id,
            "investigation_id": e.investigation_id,
            "filename": e.filename,
            "original_filename": e.original_filename,
            "media_type": e.media_type,
            "sha256": e.sha256,
            "file_size": e.file_size,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in evidence_items
    ]

    confidence_dist = {}
    for f in findings_list:
        band = f.get("confidence_band", "medium")
        confidence_dist[band] = confidence_dist.get(band, 0) + 1

    structured_facts = {}
    try:
        structured_facts = json.loads(inv.structured_facts_json) if inv.structured_facts_json else {}
    except Exception:
        structured_facts = {}

    # Calculate comprehensive forensic assessment
    assessment_obj = evaluate_investigation_findings(findings_list, correlations_list, evidence_dicts)
    assessment_dict = assessment_obj.model_dump()

    return {
        "investigation": {
            "id": inv.id,
            "title": inv.title,
            "description": inv.description,
            "reference_context": inv.reference_context,
            "structured_facts": structured_facts,
            "ai_enabled": bool(inv.ai_enabled),
            "ai_provider": inv.ai_provider,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else "",
        },
        "evidence_items": evidence_dicts,
        "findings": findings_list,
        "correlations": correlations_list,
        "assessment": assessment_dict,
        "summary": {
            "total_evidence": len(evidence_items),
            "total_findings": len(findings_list),
            "total_correlations": len(correlations_list),
            "confidence_distribution": confidence_dist,
        },
        "limitations": [
            "Automated analysis provides indicators, not conclusive verdicts.",
            "All significant findings and correlations require qualified human review.",
            "Missing EXIF or compression anomalies do not constitute definitive proof of synthetic manipulation."
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/investigations/{investigation_id}/report", response_model=ReportResponse)
def get_investigation_report(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    data = _build_report_data(inv, db)
    return ReportResponse(
        investigation=data["investigation"],
        evidence_items=data["evidence_items"],
        findings=data["findings"],
        correlations=data["correlations"],
        summary=data["summary"],
        limitations=data["limitations"],
        generated_at=datetime.now(timezone.utc),
    )

@router.get("/investigations/{investigation_id}/report/pdf")
def get_investigation_report_pdf(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    data = _build_report_data(inv, db)
    pdf_path = generate_pdf_report(data)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )

@router.get("/investigations/{investigation_id}/assessment")
def get_investigation_assessment(investigation_id: str, db: Session = Depends(get_db)):
    """Retrieve explainable forensic assessment breakdown for an investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    data = _build_report_data(inv, db)
    return data.get("assessment", {})

