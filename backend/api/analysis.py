import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Investigation, Evidence, AnalysisRun, FindingRecord, Correlation
from backend.schemas import AnalysisStatusResponse
from backend.engines.image_engine import analyze_image
from backend.engines.video_engine import analyze_video
from backend.engines.audio_engine import analyze_audio
from backend.engines.text_engine import analyze_text
from backend.correlation.correlator import correlate_findings
from backend.ai.provider_manager import get_active_provider_and_key

router = APIRouter(prefix="/api/v1", tags=["analysis"])

@router.post("/investigations/{investigation_id}/analyze", response_model=AnalysisStatusResponse)
async def run_analysis(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    evidence_items = db.query(Evidence).filter(Evidence.investigation_id == investigation_id).all()
    if not evidence_items:
        raise HTTPException(status_code=400, detail="No evidence uploaded for this investigation")

    # Create analysis run with standard PROCESSING status
    run = AnalysisRun(investigation_id=investigation_id, status="PROCESSING")
    inv.status = "analyzing"
    db.add(run)
    db.commit()
    db.refresh(run)

    all_findings = []
    errors = []
    total = len(evidence_items)

    # Optional AI provider setup if enabled on this investigation
    ai_helper = None
    if inv.ai_enabled:
        p_inst, api_key, model = get_active_provider_and_key(db, inv.ai_provider or "gemini")
        if p_inst and api_key:
            ai_helper = (p_inst, api_key, model)

    for idx, ev in enumerate(evidence_items):
        progress = {
            "current": idx + 1,
            "total": total,
            "current_file": ev.original_filename,
            "status": "analyzing",
            "percent": int(((idx) / total) * 100)
        }
        run.progress_json = json.dumps(progress)
        db.commit()

        try:
            if ev.media_type == "image":
                findings = await analyze_image(ev.id, ev.original_path, ev.media_type)
            elif ev.media_type == "video":
                findings = await analyze_video(ev.id, ev.original_path, ev.media_type)
            elif ev.media_type == "audio":
                findings = await analyze_audio(ev.id, ev.original_path, ev.media_type)
            elif ev.media_type == "text":
                findings = await analyze_text(
                    ev.id, ev.original_path, ev.media_type,
                    reference_context=inv.reference_context or "",
                    ai_helper=ai_helper
                )
            else:
                findings = []

            # Save findings to DB
            for f in findings:
                record = FindingRecord(
                    id=f.finding_id,
                    analysis_id=run.id,
                    evidence_id=f.evidence_id,
                    engine=f.engine,
                    indicator=f.indicator,
                    description=f.description,
                    location_json=json.dumps(f.location.model_dump()) if f.location else "{}",
                    model_score=f.model_score,
                    confidence_band=f.confidence_band,
                    limitations_json=json.dumps(f.limitations),
                )
                db.add(record)
                all_findings.append(f)

        except Exception as e:
            error_msg = f"Engine failure for {ev.original_filename} ({ev.media_type}): {str(e)}"
            errors.append(error_msg)

    db.commit()

    # Run Cross-Modal Correlation Engine
    try:
        correlation_results = await correlate_findings(
            all_findings, reference_context=inv.reference_context or ""
        )
        for c in correlation_results:
            corr_record = Correlation(
                id=c.correlation_id,
                analysis_id=run.id,
                source_finding_id=c.source_finding_id,
                target_finding_id=c.target_finding_id,
                source_evidence_id=c.source_evidence_id,
                target_evidence_id=c.target_evidence_id,
                relationship_type=c.relationship_type,
                explanation=c.explanation,
                strength=c.strength,
                rule_id=c.rule_id or "",
                limitations_json=json.dumps(c.limitations)
            )
            db.add(corr_record)
        db.commit()
    except Exception as e:
        errors.append(f"Correlation error: {str(e)}")
        db.commit()

    # Finalize status according to strict standards: COMPLETED, PARTIALLY_COMPLETED, or FAILED
    if not errors:
        run.status = "COMPLETED"
        inv.status = "analyzed"
    elif len(all_findings) > 0:
        run.status = "PARTIALLY_COMPLETED"
        inv.status = "analyzed"
    else:
        run.status = "FAILED"
        inv.status = "failed"

    run.completed_at = datetime.now(timezone.utc)
    run.error_message = "; ".join(errors) if errors else None
    run.progress_json = json.dumps({
        "current": total,
        "total": total,
        "status": "done",
        "findings_count": len(all_findings),
        "percent": 100
    })

    db.commit()
    db.refresh(run)

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
