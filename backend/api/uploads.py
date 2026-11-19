import json
import mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Investigation, Evidence
from backend.schemas import EvidenceResponse
from backend.config import ORIGINALS_DIR, PROCESSED_DIR
from backend.utils.file_validation import validate_upload, generate_safe_filename
from backend.forensic.hashing import compute_sha256
from backend.forensic.metadata import (
    extract_image_metadata, extract_video_metadata, extract_audio_metadata
)

router = APIRouter(prefix="/api/v1", tags=["uploads"])

@router.post("/investigations/{investigation_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def upload_evidence(
    investigation_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    content = await file.read()
    is_valid, media_type, error_msg = await validate_upload(file, content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    safe_filename = generate_safe_filename(file.filename or "unknown")
    ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = ORIGINALS_DIR / safe_filename

    with open(save_path, "wb") as f:
        f.write(content)

    sha256 = compute_sha256(save_path)

    # Extract initial metadata
    metadata = {}
    try:
        if media_type == "image":
            metadata = extract_image_metadata(str(save_path))
        elif media_type == "video":
            metadata = extract_video_metadata(str(save_path))
        elif media_type == "audio":
            metadata = extract_audio_metadata(str(save_path))
        elif media_type == "text":
            metadata = {"encoding": "utf-8", "size": len(content)}
    except Exception as e:
        metadata = {"extraction_error": str(e)}

    metadata_json = json.dumps(metadata, default=str)

    evidence = Evidence(
        investigation_id=investigation_id,
        filename=safe_filename,
        original_filename=file.filename or "unknown",
        media_type=media_type,
        original_path=str(save_path),
        sha256=sha256,
        file_size=len(content),
        metadata_json=metadata_json,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return EvidenceResponse(
        id=evidence.id,
        investigation_id=evidence.investigation_id,
        filename=evidence.filename,
        original_filename=evidence.original_filename,
        media_type=evidence.media_type,
        sha256=evidence.sha256,
        file_size=evidence.file_size,
        metadata_json=evidence.metadata_json,
        created_at=evidence.created_at,
    )

@router.get("/investigations/{investigation_id}/evidence", response_model=list[EvidenceResponse])
def list_evidence(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    items = db.query(Evidence).filter(Evidence.investigation_id == investigation_id).all()
    return [
        EvidenceResponse(
            id=e.id,
            investigation_id=e.investigation_id,
            filename=e.filename,
            original_filename=e.original_filename,
            media_type=e.media_type,
            sha256=e.sha256,
            file_size=e.file_size,
            metadata_json=e.metadata_json or "{}",
            created_at=e.created_at,
        )
        for e in items
    ]

@router.delete("/investigations/{investigation_id}/evidence/{evidence_id}")
def delete_evidence_item(
    investigation_id: str,
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete evidence before analysis.
    Safeguard: Blocked if investigation has been analyzed to preserve forensic chain of custody.
    """
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if inv.status in ["analyzing", "analyzed", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Evidence cannot be removed after analysis has commenced. Immutable forensic chain of custody."
        )

    ev = db.query(Evidence).filter(
        Evidence.id == evidence_id,
        Evidence.investigation_id == investigation_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    # Remove original file if exists
    try:
        p = Path(ev.original_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    db.delete(ev)
    db.commit()
    return {"status": "deleted", "id": evidence_id}

@router.get("/evidence/{evidence_id}/file")
def serve_evidence_file(evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    file_path = Path(evidence.original_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        filename=evidence.original_filename,
        media_type=mime_type or "application/octet-stream"
    )

@router.get("/evidence/{evidence_id}/artifact/{filename}")
def serve_artifact(evidence_id: str, filename: str, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    artifact_dir = PROCESSED_DIR / evidence_id
    artifact_path = artifact_dir / filename
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    mime_type, _ = mimetypes.guess_type(str(artifact_path))
    return FileResponse(
        path=str(artifact_path),
        filename=filename,
        media_type=mime_type or "application/octet-stream"
    )
