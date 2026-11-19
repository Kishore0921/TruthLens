import re
from backend.schemas import Finding
from backend.engines.text_engine import extract_typed_entities

def normalize_finding(finding: Finding) -> dict:
    """Extract standardized typed features from finding description, indicator, and location."""
    desc = finding.description
    typed = extract_typed_entities(desc)
    
    # Meaningful vocabulary words (excluding common forensic report terms)
    words = set(w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', desc))
    stopwords = {
        "and", "the", "for", "with", "from", "that", "this", "were", "been",
        "have", "analysis", "finding", "detected", "observed", "completed",
        "confirmed", "reported", "stream", "evidence", "properties", "indicator"
    }
    meaningful_words = words - stopwords

    return {
        "finding_id": finding.finding_id,
        "evidence_id": finding.evidence_id,
        "media_type": finding.media_type,
        "engine": finding.engine,
        "indicator": finding.indicator,
        "timestamp": finding.location.timestamp if finding.location else None,
        "frame_number": finding.location.frame_number if finding.location else None,
        "dates": typed["dates"],
        "times": typed["times"],
        "locations": typed["locations"],
        "organizations": typed["organizations"],
        "people": typed["people"],
        "words": meaningful_words,
        "confidence_band": finding.confidence_band,
        "model_score": finding.model_score,
        "raw_description": desc,
        "raw": finding
    }
