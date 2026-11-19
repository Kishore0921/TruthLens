import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Investigation, Evidence, AnalysisRun, FindingRecord, Correlation
from backend.schemas import (
    InvestigationCreate, InvestigationResponse, AnalysisStatusResponse,
    FindingResponse, CorrelationResponse, ReportResponse
)
from backend.forensic.report_generator import generate_pdf_report

router = APIRouter(prefix="/api/v1", tags=["investigations"])


@router.post("/investigations", response_model=InvestigationResponse, status_code=201)
def create_investigation(data: InvestigationCreate, db: Session = Depends(get_db)):
    inv = Investigation(
        title=data.title,
        description=data.description,
        reference_context=data.reference_context,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return InvestigationResponse(
        id=inv.id,
        title=inv.title,
        description=inv.description,
        reference_context=inv.reference_context,
        status=inv.status,
        created_at=inv.created_at,
        evidence_count=0,
        analysis_count=0,
    )


@router.get("/investigations", response_model=list[InvestigationResponse])
def list_investigations(db: Session = Depends(get_db)):
    investigations = db.query(Investigation).order_by(Investigation.created_at.desc()).all()
    results = []
    for inv in investigations:
        results.append(InvestigationResponse(
            id=inv.id,
            title=inv.title,
            description=inv.description,
            reference_context=inv.reference_context,
            status=inv.status,
            created_at=inv.created_at,
            evidence_count=len(inv.evidence_items),
            analysis_count=len(inv.analysis_runs),
        ))
    return results


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationResponse(
        id=inv.id,
        title=inv.title,
        description=inv.description,
        reference_context=inv.reference_context,
        status=inv.status,
        created_at=inv.created_at,
        evidence_count=len(inv.evidence_items),
        analysis_count=len(inv.analysis_runs),
    )


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
        raise HTTPException(status_code=404, detail="No analysis runs found")
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
    return [
        CorrelationResponse(
            id=c.id,
            analysis_id=c.analysis_id,
            source_finding_id=c.source_finding_id,
            target_finding_id=c.target_finding_id,
            relationship_type=c.relationship_type,
            explanation=c.explanation,
            strength=c.strength,
            rule_id=c.rule_id or "",
        )
        for c in correlations
    ]


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
            correlations_list.append({
                "id": c.id,
                "analysis_id": c.analysis_id,
                "source_finding_id": c.source_finding_id,
                "target_finding_id": c.target_finding_id,
                "relationship_type": c.relationship_type,
                "explanation": c.explanation,
                "strength": c.strength,
                "rule_id": c.rule_id or "",
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

    # Confidence distribution
    confidence_dist = {}
    for f in findings_list:
        band = f.get("confidence_band", "medium")
        confidence_dist[band] = confidence_dist.get(band, 0) + 1

    return {
        "investigation": {
            "id": inv.id,
            "title": inv.title,
            "description": inv.description,
            "reference_context": inv.reference_context,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else "",
        },
        "evidence_items": evidence_dicts,
        "findings": findings_list,
        "correlations": correlations_list,
        "summary": {
            "total_evidence": len(evidence_items),
            "total_findings": len(findings_list),
            "total_correlations": len(correlations_list),
            "confidence_distribution": confidence_dist,
        },
        "limitations": [
            "Automated analysis provides indicators, not conclusive proof.",
            "Results require qualified human review.",
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
