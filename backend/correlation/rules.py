import uuid
from backend.schemas import Finding, CorrelationResult
from backend.correlation.normalizer import normalize_finding

def rule_date_correlation(norm_findings: list[dict]) -> list[CorrelationResult]:
    """Compare embedded dates/timestamps across distinct evidence items."""
    correlations = []
    dated_findings = [f for f in norm_findings if f["dates"]]
    
    for i in range(len(dated_findings)):
        for j in range(i + 1, len(dated_findings)):
            f1, f2 = dated_findings[i], dated_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue
                
            dates1 = set(d.lower() for d in f1["dates"])
            dates2 = set(d.lower() for d in f2["dates"])
            
            common = dates1.intersection(dates2)
            conflict = dates1.symmetric_difference(dates2)
            
            # Check for conflict when both have explicit calendar dates
            if dates1 and dates2 and not common:
                d1_str = ", ".join(f1["dates"])
                d2_str = ", ".join(f2["dates"])
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Temporal conflict detected across media types ({f1['media_type']} vs {f2['media_type']}): "
                        f"Evidence 1 indicates '{d1_str}' while Evidence 2 indicates '{d2_str}'."
                    ),
                    strength=0.88,
                    rule_id="RULE_METADATA_DATE_CONFLICT"
                ))
            elif common:
                shared_str = ", ".join(list(common))
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    relationship_type="SUPPORTS",
                    explanation=(
                        f"Temporal alignment across evidence items ({f1['media_type']} and {f2['media_type']}): "
                        f"Both refer to confirmed timestamp/date token '{shared_str}'."
                    ),
                    strength=0.80,
                    rule_id="RULE_TEMPORAL_DATE_MATCH"
                ))
    return correlations

def rule_location_correlation(norm_findings: list[dict]) -> list[CorrelationResult]:
    """Correlate geographic entities across media items."""
    correlations = []
    loc_findings = [f for f in norm_findings if f["locations"]]
    
    for i in range(len(loc_findings)):
        for j in range(i + 1, len(loc_findings)):
            f1, f2 = loc_findings[i], loc_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue
                
            locs1 = set(l.lower() for l in f1["locations"])
            locs2 = set(l.lower() for l in f2["locations"])
            
            common = locs1.intersection(locs2)
            
            # Direct contradiction (e.g. Bangalore vs Chennai)
            if locs1 and locs2 and not common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Geographic contradiction between {f1['media_type']} evidence and {f2['media_type']} evidence: "
                        f"One references '{', '.join(f1['locations'])}' while the other references '{', '.join(f2['locations'])}'."
                    ),
                    strength=0.85,
                    rule_id="RULE_GEOGRAPHIC_CONTRADICTION"
                ))
            elif common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    relationship_type="RELATED",
                    explanation=(
                        f"Common geographic location '{', '.join(list(common)).title()}' linked across "
                        f"{f1['media_type']} and {f2['media_type']} evidence."
                    ),
                    strength=0.75,
                    rule_id="RULE_GEOGRAPHIC_CO_OCCURRENCE"
                ))
    return correlations

def rule_temporal_alignment(norm_findings: list[dict]) -> list[CorrelationResult]:
    """Correlate timestamps between video frames and audio observations."""
    correlations = []
    video_findings = [f for f in norm_findings if f["media_type"] == "video" and f["timestamp"] is not None]
    audio_findings = [f for f in norm_findings if f["media_type"] == "audio" and f["timestamp"] is not None]
    
    for vf in video_findings:
        for af in audio_findings:
            if vf["evidence_id"] == af["evidence_id"]:
                continue
            delta = abs(vf["timestamp"] - af["timestamp"])
            if delta <= 1.5:  # Within 1.5 seconds window
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=vf["finding_id"],
                    target_finding_id=af["finding_id"],
                    relationship_type="TIME_ALIGNED",
                    explanation=(
                        f"Cross-modal temporal sync: Video observation at {vf['timestamp']:.2f}s "
                        f"aligns with audio window at {af['timestamp']:.2f}s (Δ={delta:.2f}s)."
                    ),
                    strength=round(max(0.4, 0.9 - (delta * 0.3)), 2),
                    rule_id="RULE_AUDIO_VIDEO_TIME_ALIGNMENT"
                ))
    return correlations

def rule_entity_cross_reference(norm_findings: list[dict]) -> list[CorrelationResult]:
    """Correlate shared named entities across evidence."""
    correlations = []
    entity_findings = [f for f in norm_findings if f["entities"]]
    
    for i in range(len(entity_findings)):
        for j in range(i + 1, len(entity_findings)):
            f1, f2 = entity_findings[i], entity_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue
                
            e1 = set(e.lower() for e in f1["entities"])
            e2 = set(e.lower() for e in f2["entities"])
            common = e1.intersection(e2)
            
            if common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    relationship_type="RELATED",
                    explanation=(
                        f"Shared entity cross-reference: Both {f1['media_type']} and {f2['media_type']} "
                        f"reference entity '{', '.join(common).title()}'."
                    ),
                    strength=0.70,
                    rule_id="RULE_NAMED_ENTITY_CROSS_REF"
                ))
    return correlations

def rule_content_similarity(norm_findings: list[dict]) -> list[CorrelationResult]:
    """Identify candidates for same event or duplicate content via vocabulary similarity."""
    correlations = []
    
    for i in range(len(norm_findings)):
        for j in range(i + 1, len(norm_findings)):
            f1, f2 = norm_findings[i], norm_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue
                
            w1 = f1["words"]
            w2 = f2["words"]
            if len(w1) >= 4 and len(w2) >= 4:
                inter = len(w1.intersection(w2))
                union = len(w1.union(w2))
                jaccard = inter / union if union > 0 else 0.0
                
                if jaccard >= 0.35:
                    correlations.append(CorrelationResult(
                        correlation_id=str(uuid.uuid4()),
                        source_finding_id=f1["finding_id"],
                        target_finding_id=f2["finding_id"],
                        relationship_type="SAME_CONTENT_CANDIDATE",
                        explanation=(
                            f"Heuristic content similarity (Jaccard={jaccard:.2f}): Findings across "
                            f"{f1['media_type']} and {f2['media_type']} evidence display significant lexical overlap ({inter} terms)."
                        ),
                        strength=round(jaccard, 2),
                        rule_id="RULE_VOCABULARY_CONTENT_SIMILARITY"
                    ))
    return correlations

def apply_all_rules(findings: list[Finding], reference_context: str = "") -> list[CorrelationResult]:
    """Execute deterministic cross-modal correlation pipeline on all normalized findings."""
    norm_findings = [normalize_finding(f) for f in findings]
    
    all_correlations: list[CorrelationResult] = []
    all_correlations.extend(rule_date_correlation(norm_findings))
    all_correlations.extend(rule_location_correlation(norm_findings))
    all_correlations.extend(rule_temporal_alignment(norm_findings))
    all_correlations.extend(rule_entity_cross_reference(norm_findings))
    all_correlations.extend(rule_content_similarity(norm_findings))
    
    # Deduplicate paired relationships
    seen_pairs = set()
    unique_correlations = []
    for c in all_correlations:
        pair_key = tuple(sorted([c.source_finding_id, c.target_finding_id])) + (c.relationship_type,)
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            unique_correlations.append(c)
            
    return unique_correlations
