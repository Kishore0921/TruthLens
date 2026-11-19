import uuid
from backend.schemas import Finding, CorrelationResult
from backend.correlation.normalizer import normalize_finding
from backend.engines.text_engine import extract_typed_entities

def rule_reference_baseline_comparison(norm_findings: list[dict], reference_context: str) -> list[CorrelationResult]:
    """
    Capability A: Reference comparison.
    Compare extracted typed facts from evidence against the investigation reference baseline.
    """
    correlations = []
    if not reference_context or not reference_context.strip():
        return correlations

    ref_typed = extract_typed_entities(reference_context)
    ref_locs = {l.lower(): l for l in ref_typed["locations"]}
    ref_dates = {d.lower(): d for d in ref_typed["dates"]}

    for f in norm_findings:
        # Check Location against reference
        f_locs = {l.lower(): l for l in f["locations"]}
        if f_locs and ref_locs:
            common = set(f_locs.keys()).intersection(set(ref_locs.keys()))
            diff_f = [f_locs[k] for k in set(f_locs.keys()) - set(ref_locs.keys())]
            diff_r = [ref_locs[k] for k in set(ref_locs.keys()) - set(f_locs.keys())]

            if diff_f and diff_r:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f["finding_id"],
                    target_finding_id=f["finding_id"],
                    source_evidence_id=f["evidence_id"],
                    target_evidence_id=None,
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Geographic contradiction against reference baseline: {f['media_type'].capitalize()} evidence "
                        f"indicates location '{', '.join(diff_f)}' whereas baseline specifies '{', '.join(diff_r)}'."
                    ),
                    strength=0.90,
                    rule_id="RULE_REF_LOCATION_CONFLICT",
                    limitations=["Compares stated location against user-supplied reference baseline; does not verify independent physical truth."]
                ))
            elif common:
                shared = [f_locs[k] for k in common]
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f["finding_id"],
                    target_finding_id=f["finding_id"],
                    source_evidence_id=f["evidence_id"],
                    target_evidence_id=None,
                    relationship_type="SUPPORTS",
                    explanation=(
                        f"Geographic corroboration with reference baseline: {f['media_type'].capitalize()} evidence "
                        f"confirms reported location '{', '.join(shared)}'."
                    ),
                    strength=0.85,
                    rule_id="RULE_REF_LOCATION_SUPPORT",
                    limitations=["Corroborates location mention with baseline."]
                ))

        # Check Date against reference
        f_dates = {d.lower(): d for d in f["dates"]}
        if f_dates and ref_dates:
            common_d = set(f_dates.keys()).intersection(set(ref_dates.keys()))
            diff_fd = [f_dates[k] for k in set(f_dates.keys()) - set(ref_dates.keys())]
            diff_rd = [ref_dates[k] for k in set(ref_dates.keys()) - set(f_dates.keys())]

            if diff_fd and diff_rd:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f["finding_id"],
                    target_finding_id=f["finding_id"],
                    source_evidence_id=f["evidence_id"],
                    target_evidence_id=None,
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Date conflict with reference baseline: {f['media_type'].capitalize()} evidence "
                        f"reports '{', '.join(diff_fd)}' while baseline reports '{', '.join(diff_rd)}'."
                    ),
                    strength=0.88,
                    rule_id="RULE_REF_DATE_CONFLICT",
                    limitations=["Calendar and weekday token comparison."]
                ))
            elif common_d:
                shared_d = [f_dates[k] for k in common_d]
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f["finding_id"],
                    target_finding_id=f["finding_id"],
                    source_evidence_id=f["evidence_id"],
                    target_evidence_id=None,
                    relationship_type="SUPPORTS",
                    explanation=(
                        f"Temporal corroboration with reference baseline: {f['media_type'].capitalize()} evidence "
                        f"confirms date token '{', '.join(shared_d)}'."
                    ),
                    strength=0.85,
                    rule_id="RULE_REF_DATE_SUPPORT",
                    limitations=["Confirmed date token alignment."]
                ))

    return correlations

def rule_date_correlation(norm_findings: list[dict]) -> list[CorrelationResult]:
    """
    Capability C: Date and time comparison across evidence files.
    Identifies conflicting or corroborating calendar dates across media items.
    """
    correlations = []
    dated_findings = [f for f in norm_findings if f["dates"]]

    for i in range(len(dated_findings)):
        for j in range(i + 1, len(dated_findings)):
            f1, f2 = dated_findings[i], dated_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue

            dates1 = {d.lower(): d for d in f1["dates"]}
            dates2 = {d.lower(): d for d in f2["dates"]}
            common = set(dates1.keys()).intersection(set(dates2.keys()))

            if dates1 and dates2 and not common:
                d1_str = ", ".join(dates1.values())
                d2_str = ", ".join(dates2.values())
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    source_evidence_id=f1["evidence_id"],
                    target_evidence_id=f2["evidence_id"],
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Temporal conflict between {f1['media_type']} evidence and {f2['media_type']} evidence: "
                        f"Evidence 1 indicates '{d1_str}' whereas Evidence 2 indicates '{d2_str}'."
                    ),
                    strength=0.88,
                    rule_id="RULE_METADATA_DATE_CONFLICT",
                    limitations=["Device timestamps depend on device clock accuracy and can be modified."]
                ))
            elif common:
                shared_str = ", ".join([dates1[k] for k in common])
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    source_evidence_id=f1["evidence_id"],
                    target_evidence_id=f2["evidence_id"],
                    relationship_type="SUPPORTS",
                    explanation=(
                        f"Temporal alignment across evidence items ({f1['media_type']} and {f2['media_type']}): "
                        f"Both refer to confirmed timestamp/date '{shared_str}'."
                    ),
                    strength=0.80,
                    rule_id="RULE_TEMPORAL_DATE_MATCH",
                    limitations=["Date token match across containers."]
                ))
    return correlations

def rule_location_correlation(norm_findings: list[dict]) -> list[CorrelationResult]:
    """
    Capability B: Cross-media entity comparison (Location <-> Location).
    Strictly compares typed locations; never compares unrelated words.
    """
    correlations = []
    loc_findings = [f for f in norm_findings if f["locations"]]

    for i in range(len(loc_findings)):
        for j in range(i + 1, len(loc_findings)):
            f1, f2 = loc_findings[i], loc_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue

            locs1 = {l.lower(): l for l in f1["locations"]}
            locs2 = {l.lower(): l for l in f2["locations"]}
            common = set(locs1.keys()).intersection(set(locs2.keys()))

            if locs1 and locs2 and not common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    source_evidence_id=f1["evidence_id"],
                    target_evidence_id=f2["evidence_id"],
                    relationship_type="CONTRADICTS",
                    explanation=(
                        f"Geographic contradiction between {f1['media_type']} evidence and {f2['media_type']} evidence: "
                        f"One references location '{', '.join(locs1.values())}' while the other references '{', '.join(locs2.values())}'."
                    ),
                    strength=0.85,
                    rule_id="RULE_GEOGRAPHIC_CONTRADICTION",
                    limitations=["Typed location comparison; does not evaluate whether multiple venues were involved."]
                ))
            elif common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    source_evidence_id=f1["evidence_id"],
                    target_evidence_id=f2["evidence_id"],
                    relationship_type="RELATED",
                    explanation=(
                        f"Common geographic location '{', '.join([locs1[k] for k in common])}' linked across "
                        f"{f1['media_type']} and {f2['media_type']} evidence."
                    ),
                    strength=0.75,
                    rule_id="RULE_GEOGRAPHIC_CO_OCCURRENCE",
                    limitations=["Common location mention."]
                ))
    return correlations

def rule_temporal_alignment(norm_findings: list[dict]) -> list[CorrelationResult]:
    """
    Capability E: Video and audio relationships.
    Connects video sampled frames and audio acoustic windows by timestamp.
    """
    correlations = []
    video_findings = [f for f in norm_findings if f["media_type"] == "video" and f["timestamp"] is not None]
    audio_findings = [f for f in norm_findings if f["media_type"] == "audio" and f["timestamp"] is not None]

    for vf in video_findings:
        for af in audio_findings:
            if vf["evidence_id"] == af["evidence_id"]:
                continue
            delta = abs(vf["timestamp"] - af["timestamp"])
            if delta <= 1.5:  # Within 1.5s tolerance
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=vf["finding_id"],
                    target_finding_id=af["finding_id"],
                    source_evidence_id=vf["evidence_id"],
                    target_evidence_id=af["evidence_id"],
                    relationship_type="TIME_ALIGNED",
                    explanation=(
                        f"Cross-modal temporal sync: Video observation at {vf['timestamp']:.2f}s "
                        f"aligns with audio acoustic window at {af['timestamp']:.2f}s (Δ={delta:.2f}s)."
                    ),
                    strength=round(max(0.4, 0.9 - (delta * 0.3)), 2),
                    rule_id="RULE_AUDIO_VIDEO_TIME_ALIGNMENT",
                    limitations=["Timestamp alignment based on container stream clocks; assumes synchronized recording."]
                ))
    return correlations

def rule_entity_cross_reference(norm_findings: list[dict]) -> list[CorrelationResult]:
    """
    Capability B: Cross-media entity comparison (Organizations and People).
    """
    correlations = []
    entity_findings = [f for f in norm_findings if (f["organizations"] or f["people"])]

    for i in range(len(entity_findings)):
        for j in range(i + 1, len(entity_findings)):
            f1, f2 = entity_findings[i], entity_findings[j]
            if f1["evidence_id"] == f2["evidence_id"]:
                continue

            ents1 = set(e.lower() for e in (f1["organizations"] + f1["people"]))
            ents2 = set(e.lower() for e in (f2["organizations"] + f2["people"]))
            common = ents1.intersection(ents2)

            if common:
                correlations.append(CorrelationResult(
                    correlation_id=str(uuid.uuid4()),
                    source_finding_id=f1["finding_id"],
                    target_finding_id=f2["finding_id"],
                    source_evidence_id=f1["evidence_id"],
                    target_evidence_id=f2["evidence_id"],
                    relationship_type="RELATED",
                    explanation=(
                        f"Shared entity cross-reference: Both {f1['media_type']} and {f2['media_type']} "
                        f"reference entity '{', '.join(common).title()}'."
                    ),
                    strength=0.72,
                    rule_id="RULE_NAMED_ENTITY_CROSS_REF",
                    limitations=["Named entity co-occurrence in independent evidence files."]
                ))
    return correlations

def rule_content_similarity(norm_findings: list[dict]) -> list[CorrelationResult]:
    """
    Capability D & G: Content similarity analysis across findings.
    Identifies candidate identical sources or corroborating accounts.
    """
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
                        source_evidence_id=f1["evidence_id"],
                        target_evidence_id=f2["evidence_id"],
                        relationship_type="SAME_CONTENT_CANDIDATE",
                        explanation=(
                            f"Heuristic content similarity (Jaccard={jaccard:.2f}): Findings across "
                            f"{f1['media_type']} and {f2['media_type']} evidence display significant lexical overlap ({inter} shared terms)."
                        ),
                        strength=round(jaccard, 2),
                        rule_id="RULE_VOCABULARY_CONTENT_SIMILARITY",
                        limitations=["Lexical vocabulary overlap; does not confirm identical author or device."]
                    ))
    return correlations

def apply_all_rules(findings: list[Finding], reference_context: str = "") -> list[CorrelationResult]:
    """
    Execute deterministic cross-modal correlation pipeline on all normalized findings.
    Never creates arbitrary relationships.
    """
    norm_findings = [normalize_finding(f) for f in findings]

    all_correlations: list[CorrelationResult] = []
    # 1. Reference baseline comparison
    all_correlations.extend(rule_reference_baseline_comparison(norm_findings, reference_context))
    # 2. Cross-evidence date conflicts & matches
    all_correlations.extend(rule_date_correlation(norm_findings))
    # 3. Cross-evidence location conflicts & matches
    all_correlations.extend(rule_location_correlation(norm_findings))
    # 4. Audio-video temporal alignment
    all_correlations.extend(rule_temporal_alignment(norm_findings))
    # 5. Shared named entities
    all_correlations.extend(rule_entity_cross_reference(norm_findings))
    # 6. Content lexical similarity
    all_correlations.extend(rule_content_similarity(norm_findings))

    # Deduplicate paired relationships
    seen_pairs = set()
    unique_correlations = []
    for c in all_correlations:
        pair_key = (
            tuple(sorted([c.source_finding_id or "", c.target_finding_id or ""])) +
            (c.relationship_type, c.rule_id)
        )
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            unique_correlations.append(c)

    return unique_correlations
