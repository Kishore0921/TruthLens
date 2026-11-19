import uuid
import re
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation

# Known major cities and locations for deterministic forensic matching
KNOWN_LOCATIONS = {
    "bangalore", "bengaluru", "chennai", "mumbai", "delhi", "new delhi", "kolkata",
    "hyderabad", "pune", "ahmedabad", "jaipur", "london", "paris", "tokyo",
    "new york", "washington", "los angeles", "berlin", "san francisco", "chicago",
    "singapore", "dubai", "sydney", "geneva", "beijing", "seoul", "kyiv", "moscow"
}

DAYS_OF_WEEK = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"}

def extract_entities_from_text(text: str) -> dict:
    """Extract deterministic entities: dates, locations, numbers, capitalized phrases."""
    text_lower = text.lower()
    
    # 1. Dates / Days
    dates_found = []
    # Standard YYYY-MM-DD or DD/MM/YYYY
    iso_dates = re.findall(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', text)
    uk_dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
    dates_found.extend(iso_dates)
    dates_found.extend(uk_dates)
    
    # Days and Month mentions
    for day in DAYS_OF_WEEK:
        if re.search(r'\b' + day + r'\b', text_lower):
            dates_found.append(day.capitalize())
            
    for month in MONTHS:
        m_matches = re.findall(r'\b' + month + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b', text_lower)
        if m_matches:
            dates_found.extend([m.title() for m in m_matches])

    # 2. Locations
    locations_found = []
    # Prepositional patterns: in Bangalore, at Chennai, from Delhi
    prep_locs = re.findall(r'\b(?:in|at|from|near|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
    for loc in prep_locs:
        locations_found.append(loc)
        
    # Check known location dictionary
    for loc in KNOWN_LOCATIONS:
        if re.search(r'\b' + loc + r'\b', text_lower):
            locations_found.append(loc.title())
    locations_found = list(dict.fromkeys(locations_found))

    # 3. Numeric claims
    numeric_claims = re.findall(r'\b(?:\$\s*)?\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:people|casualties|dollars|crore|lakh|percent|%|hours|minutes|seconds|days|miles|km))?\b', text, re.IGNORECASE)

    # 4. Named entities (Capitalized phrases that aren't starting sentences)
    # Match 2-4 word Title Cased sequences
    named_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    named_entities = [ne for ne in named_entities if not any(d in ne for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])]

    return {
        "dates": list(set(dates_found)),
        "locations": locations_found,
        "numerics": numeric_claims[:8],
        "named_entities": list(set(named_entities))[:10]
    }

async def analyze_text(evidence_id: str, filepath: str, media_type: str, reference_context: str = "") -> list[Finding]:
    findings: list[Finding] = []

    # 1. Read and Normalize
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="text",
            engine="text_loader",
            indicator="read_error",
            description=f"Could not read text file: {str(e)}",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="high",
            limitations=["File access or character decoding failure"]
        ))
        return findings

    normalized_text = " ".join(content.split())
    words = re.findall(r'\b\w+\b', normalized_text)
    word_count = len(words)
    char_count = len(normalized_text)
    
    # Split sentences on ., !, ?
    raw_sentences = [s.strip() for s in re.split(r'[.!?]+', normalized_text) if s.strip()]
    sentence_count = len(raw_sentences)

    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="text",
        engine="text_corpus_metrics",
        indicator="structural_counts",
        description=f"Text corpus metrics: {word_count} words, {char_count} characters, {sentence_count} sentences extracted.",
        location=EvidenceLocation(),
        model_score=None,
        confidence_band="high",
        limitations=["Strictly morphological counts; does not evaluate semantic coherence"]
    ))

    # 2. Entity and Keyword Extraction
    entities = extract_entities_from_text(content)
    
    entity_summary_parts = []
    if entities["locations"]:
        entity_summary_parts.append(f"Locations: {', '.join(entities['locations'])}")
    if entities["dates"]:
        entity_summary_parts.append(f"Temporal/Dates: {', '.join(entities['dates'])}")
    if entities["named_entities"]:
        entity_summary_parts.append(f"Named entities: {', '.join(entities['named_entities'])}")
    if entities["numerics"]:
        entity_summary_parts.append(f"Numeric claims: {', '.join(entities['numerics'][:5])}")

    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="text",
        engine="entity_extractor",
        indicator="extracted_entities",
        description="Extracted entities: " + ("; ".join(entity_summary_parts) if entity_summary_parts else "No specific standard entities identified."),
        location=EvidenceLocation(),
        model_score=None,
        confidence_band="medium",
        limitations=[
            "Entity extraction uses deterministic rule patterns and gazetteers, NOT full deep learning NER",
            "Complex context or unorthodox syntax may be omitted or misclassified"
        ]
    ))

    # 3. Reference Context Comparison (if provided)
    if reference_context and reference_context.strip():
        ref_text = reference_context.strip()
        ref_words = set(re.findall(r'\b\w+\b', ref_text.lower()))
        doc_words = set(w.lower() for w in words)

        # Lexical Jaccard overlap
        intersection = doc_words.intersection(ref_words)
        union = doc_words.union(ref_words)
        jaccard = len(intersection) / len(union) if union else 0.0

        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="text",
            engine="text_reference_comparator",
            indicator="lexical_overlap_similarity",
            description=f"Lexical overlap with reference context: Jaccard similarity={jaccard:.2f} ({len(intersection)} shared vocabulary tokens).",
            location=EvidenceLocation(),
            model_score=round(jaccard, 3),
            confidence_band="high",
            limitations=[
                "Word overlap indicates vocabulary sharing, not semantic agreement",
                "Synonymous phrasing with distinct words will yield low lexical overlap"
            ]
        ))

        # Contradiction and discrepancy analysis
        ref_entities = extract_entities_from_text(ref_text)
        
        # Check Location Discrepancies
        text_locs = set(l.lower() for l in entities["locations"])
        ref_locs = set(l.lower() for l in ref_entities["locations"])
        
        if text_locs and ref_locs:
            common_locs = text_locs.intersection(ref_locs)
            diff_text = text_locs - ref_locs
            diff_ref = ref_locs - text_locs

            if diff_text and diff_ref:
                # Direct location contradiction pattern (e.g., Bangalore vs Chennai)
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_contradiction_engine",
                    indicator="location_mismatch_detected",
                    description=(
                        f"Location discrepancy detected: Text specifies '{', '.join(t.capitalize() for t in diff_text)}' "
                        f"whereas reference context specifies '{', '.join(r.capitalize() for r in diff_ref)}'. "
                        f"Potential geographic conflict in reported incident."
                    ),
                    location=EvidenceLocation(),
                    model_score=0.85,
                    confidence_band="medium",
                    limitations=[
                        "Rule-based entity mismatch detection; does not verify if multiple events occurred at distinct locations",
                        "Does not possess deep semantic comprehension; human analyst must verify context"
                    ]
                ))
            elif common_locs:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_corroboration_engine",
                    indicator="location_concordance",
                    description=f"Geographic concordance: Both text evidence and reference context specify '{', '.join(c.capitalize() for c in common_locs)}'.",
                    location=EvidenceLocation(),
                    model_score=0.90,
                    confidence_band="high",
                    limitations=["Corroborates location mention; does not independently verify incident reality"]
                ))

        # Check Temporal / Day / Date Discrepancies
        text_dates = set(d.lower() for d in entities["dates"])
        ref_dates = set(d.lower() for d in ref_entities["dates"])
        if text_dates and ref_dates:
            diff_td = text_dates - ref_dates
            diff_rd = ref_dates - text_dates
            if diff_td and diff_rd:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_contradiction_engine",
                    indicator="temporal_mismatch_detected",
                    description=(
                        f"Temporal discrepancy detected: Text specifies '{', '.join(d.capitalize() for d in diff_td)}' "
                        f"whereas reference context specifies '{', '.join(d.capitalize() for d in diff_rd)}'."
                    ),
                    location=EvidenceLocation(),
                    model_score=0.80,
                    confidence_band="medium",
                    limitations=["Evaluated via deterministic date token matching"]
                ))

    return findings
