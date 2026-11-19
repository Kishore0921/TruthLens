from typing import Any
from pydantic import BaseModel, Field

class ForensicAssessment(BaseModel):
    primary_status: str  # NO_STRONG_INDICATORS, POTENTIAL_INDICATORS, STRONG_INDICATORS, AI_GENERATED_INDICATORS, CONFLICTING_FINDINGS, INSUFFICIENT_EVIDENCE
    badge_label: str
    headline: str
    summary_narrative: str
    observations_count: int = 0
    heuristics_flagged_count: int = 0
    models_flagged_count: int = 0
    contradictions_count: int = 0
    key_observations: list[str] = Field(default_factory=list)
    flagged_indicators: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    limitations_and_disclaimers: list[str] = Field(default_factory=list)


def evaluate_investigation_findings(
    findings: list[dict[str, Any]],
    correlations: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]]
) -> ForensicAssessment:
    """
    Evaluates multimodal findings and correlations to produce an explainable forensic assessment.
    Core principle: Scores and heuristic flags are indicators, not definitive verdicts.
    """
    if not evidence_items or not findings:
        return ForensicAssessment(
            primary_status="INSUFFICIENT_EVIDENCE",
            badge_label="Insufficient Evidence",
            headline="Analysis Incomplete or Evidence Unprocessed",
            summary_narrative="No forensic findings or processed evidence items are available to form an assessment.",
            limitations_and_disclaimers=[
                "Forensic assessment requires completed signal analysis on at least one evidence item."
            ]
        )

    direct_observations = []
    heuristic_flags = []
    model_flags = []
    contradictions = []

    for f in findings:
        engine = f.get("engine", "")
        indicator = f.get("indicator", "")
        desc = f.get("description", "")
        band = f.get("confidence_band", "medium")
        score = f.get("model_score")

        # Category: Direct Observation
        if any(term in engine for term in ["properties", "metadata", "container_info", "validator"]) or "timestamp" in indicator:
            direct_observations.append(desc)
            continue

        # Check for model / heuristic flags
        if score is not None:
            # Score above 0.5 indicates elevated anomaly
            if score >= 0.5:
                item = {
                    "engine": engine,
                    "indicator": indicator,
                    "description": desc,
                    "score": score,
                    "confidence_band": band,
                    "limitations": f.get("limitations", [])
                }
                if any(m in engine for m in ["frequency_spectral", "local_noise", "temporal_consistency", "synthetic_speech"]):
                    model_flags.append(item)
                else:
                    heuristic_flags.append(item)
        elif band == "high" and any(k in indicator for k in ["anomaly", "divergence", "inconsistency", "manipulation"]):
            heuristic_flags.append({
                "engine": engine,
                "indicator": indicator,
                "description": desc,
                "score": None,
                "confidence_band": band,
                "limitations": f.get("limitations", [])
            })

    # Cross-modal contradictions
    for c in correlations:
        rel = c.get("relationship_type", "")
        if rel == "CONTRADICTS":
            contradictions.append({
                "explanation": c.get("explanation", ""),
                "strength": c.get("strength", 0.0),
                "rule_id": c.get("rule_id", ""),
                "limitations": c.get("limitations", [])
            })

    # Determine Primary Status
    has_contradictions = len(contradictions) > 0
    has_model_flags = len(model_flags) > 0
    has_heuristic_flags = len(heuristic_flags) > 0

    if has_contradictions and (has_model_flags or has_heuristic_flags):
        primary_status = "STRONG_INDICATORS"
        badge_label = "Strong Indicators Detected"
        headline = "Multiple Independent Manipulation Indicators and Cross-Modal Contradictions Flagged"
        narrative = (
            f"The multimodal analysis identified {len(contradictions)} cross-modal factual contradiction(s) "
            f"alongside {len(model_flags) + len(heuristic_flags)} anomalous signal/compression indicators. "
            f"These findings suggest potential synthesis, splicing, or contextual misrepresentation."
        )
    elif has_contradictions:
        primary_status = "CONFLICTING_FINDINGS"
        badge_label = "Cross-Modal Contradictions"
        headline = "Discrepancies Observed Between Media Modalities or Reference Context"
        narrative = (
            f"Cross-modal correlation identified {len(contradictions)} conflicting data point(s) "
            f"(e.g., date, location, or visual entity contradictions) across the provided evidence."
        )
    elif has_model_flags:
        # Check if model flags are AI generation specific
        is_ai_spec = any("frequency" in m["engine"] or "synthetic" in m["engine"] for m in model_flags)
        if is_ai_spec:
            primary_status = "AI_GENERATED_INDICATORS"
            badge_label = "AI Generation Indicators"
            headline = "Signal Patterns Characteristic of Generative AI Synthesis Observed"
            narrative = (
                f"Specialized signal analysis detected {len(model_flags)} pattern(s) characteristic of "
                f"generative synthesis (e.g. 2D-FFT periodic grid dispersion, acoustic vocoder attenuation, or sensor noise absence)."
            )
        else:
            primary_status = "POTENTIAL_INDICATORS"
            badge_label = "Potential Indicators"
            headline = "Isolated Structural or Temporal Anomalies Detected"
            narrative = (
                f"Signal analysis flagged {len(model_flags)} potential anomaly score(s). "
                f"Evidence exhibits localized divergence that warrants analyst review."
            )
    elif has_heuristic_flags:
        primary_status = "POTENTIAL_INDICATORS"
        badge_label = "Potential Indicators"
        headline = "Heuristic Compression or Distribution Discrepancies Noted"
        narrative = (
            f"Error Level Analysis or channel distributions flagged {len(heuristic_flags)} localized variation(s). "
            f"These may reflect legitimate re-encoding, varying texture complexity, or editing."
        )
    else:
        primary_status = "NO_STRONG_INDICATORS"
        badge_label = "No Strong Indicators"
        headline = "No High-Confidence Tampering or Synthesis Signatures Identified"
        narrative = (
            "Empirical forensic checks across all modalities revealed uniform compression characteristics, "
            "standard sensor noise distribution, and consistent metadata without cross-modal contradictions."
        )

    disclaimers = [
        "A forensic detection score is an indicator, NOT a definitive verdict of forgery or authenticity.",
        "Absence of detectable anomalies does not prove an asset has not been subtly manipulated or generated.",
        "Error Level Analysis and noise variance can be influenced by standard re-saving, social media recompression, or complex natural textures.",
        "Missing EXIF or container metadata does not prove manipulation, as many communication platforms automatically strip metadata for privacy.",
        "All algorithmic observations must be verified by a qualified human forensic investigator."
    ]

    return ForensicAssessment(
        primary_status=primary_status,
        badge_label=badge_label,
        headline=headline,
        summary_narrative=narrative,
        observations_count=len(direct_observations),
        heuristics_flagged_count=len(heuristic_flags),
        models_flagged_count=len(model_flags),
        contradictions_count=len(contradictions),
        key_observations=direct_observations[:8],
        flagged_indicators=model_flags + heuristic_flags,
        contradictions=contradictions,
        limitations_and_disclaimers=disclaimers
    )
