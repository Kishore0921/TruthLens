import uuid
import re
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation

# Comprehensive verified gazetteer of major cities, countries, and regions
KNOWN_LOCATIONS = {
    # India
    "bangalore", "bengaluru", "chennai", "mumbai", "delhi", "new delhi", "kolkata",
    "hyderabad", "pune", "ahmedabad", "jaipur", "kochi", "cochin", "goa", "kerala",
    "karnataka", "tamil nadu", "chandigarh", "lucknow", "bhopal", "guwahati",
    # Global
    "london", "paris", "tokyo", "new york", "washington", "los angeles", "berlin",
    "san francisco", "chicago", "singapore", "dubai", "sydney", "geneva", "beijing",
    "seoul", "kyiv", "moscow", "toronto", "vancouver", "zurich", "rome", "madrid",
    "amsterdam", "brussels", "ottawa", "hong kong", "melbourne", "frankfurt", "vienna"
}

# Explicit negative blocklist of non-location English nouns that often follow prepositions
NON_LOCATION_WORDS = {
    "skills", "brief", "report", "meeting", "conference", "session", "summit",
    "protocols", "initiatives", "discussions", "proceedings", "talks", "review",
    "detail", "fact", "summary", "context", "addition", "response", "attendance",
    "terms", "line", "accordance", "favor", "lieu", "spite", "regard", "reference",
    "delegates", "attendees", "security", "digital", "technology", "cybersecurity",
    "infrastructure", "intelligence", "operations", "order", "practice", "principle"
}

DAYS_OF_WEEK = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

# Common organization suffixes and known patterns
ORG_PATTERNS = [
    r'\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\s+(?:Corporation|Corp|Inc|Ltd|Limited|LLC|Group|Technologies|Foundation|Department|Agency|Ministry|Commission|Committee|Board|University|Institute)\b',
    r'\b(?:UN|NATO|WHO|FBI|CIA|EU|CBI|ISRO|NASA|INTERPOL|CERT)\b'
]

# Time regex patterns
TIME_PATTERNS = [
    r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm|UTC|GMT|IST|EST|PST)?\b',
    r'\b(?:morning|afternoon|evening|night|midnight|noon)\b'
]

def extract_typed_entities(text: str) -> dict:
    """
    Extract typed, categorized entities with strict type integrity:
    Location, Date, Time, Person, Organization, Numeric.
    Never categorizes abstract nouns (e.g. 'Skills') as locations.
    """
    text_lower = text.lower()

    # 1. Dates / Temporal
    dates_found = []
    # ISO & common numeric dates: YYYY-MM-DD, DD/MM/YYYY
    for p in [r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b']:
        dates_found.extend(re.findall(p, text))

    for day in DAYS_OF_WEEK:
        if re.search(r'\b' + day + r'\b', text_lower):
            dates_found.append(day.capitalize())

    for month in MONTHS:
        matches = re.findall(r'\b' + month + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b', text_lower)
        dates_found.extend([m.title() for m in matches])

    # 2. Times
    times_found = []
    for tp in TIME_PATTERNS:
        times_found.extend(re.findall(tp, text, re.IGNORECASE))

    # 3. Locations (Strict gazetteer + validated prepositional check)
    locations_found = []
    # Check verified gazetteer first
    for loc in KNOWN_LOCATIONS:
        if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
            locations_found.append(loc.title())

    # Prepositional pattern: in X, at Y, from Z
    prep_matches = re.findall(r'\b(?:in|at|from|near|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
    for candidate in prep_matches:
        cand_clean = candidate.strip()
        cand_lower = cand_clean.lower()
        # Verify candidate is NOT a common noun/abstract word
        words_in_cand = set(cand_lower.split())
        if not words_in_cand.intersection(NON_LOCATION_WORDS):
            if cand_lower in KNOWN_LOCATIONS or cand_clean.endswith(("City", "Center", "Hall", "Square", "Airport", "Street", "Avenue", "Station")):
                locations_found.append(cand_clean)

    locations_found = list(dict.fromkeys(locations_found))

    # 4. Organizations
    orgs_found = []
    for op in ORG_PATTERNS:
        orgs_found.extend(re.findall(op, text))
    orgs_found = list(dict.fromkeys(orgs_found))

    # 5. People / Names (Formal titles or two-word capitalized patterns not matching orgs or locations)
    people_found = []
    person_titles = re.findall(r'\b(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.|Minister|President|Director|Officer|Chief)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text)
    people_found.extend(person_titles)
    people_found = list(dict.fromkeys(people_found))

    # 6. Numerics
    numerics = re.findall(r'\b(?:\$\s*)?\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:people|delegates|attendees|casualties|crore|lakh|percent|%|hours|minutes|seconds|days|miles|km|dollars))?\b', text, re.IGNORECASE)

    return {
        "dates": list(dict.fromkeys(dates_found)),
        "times": list(dict.fromkeys(times_found)),
        "locations": locations_found,
        "organizations": orgs_found,
        "people": people_found,
        "numerics": numerics[:8]
    }

def extract_text_from_file(filepath: str) -> str:
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pypdf
        reader = pypdf.PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts)
    elif ext in [".docx", ".doc"]:
        import docx
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    else:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

async def analyze_text(
    evidence_id: str,
    filepath: str,
    media_type: str,
    reference_context: str = "",
    ai_helper: tuple = None
) -> list[Finding]:
    findings: list[Finding] = []

    # 1. Read & Normalize (supports .txt, .pdf, .docx)
    try:
        content = extract_text_from_file(filepath)
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

    # 2. Typed Entity Extraction
    entities = extract_typed_entities(content)
    
    entity_parts = []
    if entities["locations"]:
        entity_parts.append(f"Locations: {', '.join(entities['locations'])}")
    if entities["dates"]:
        entity_parts.append(f"Dates: {', '.join(entities['dates'])}")
    if entities["times"]:
        entity_parts.append(f"Times: {', '.join(entities['times'])}")
    if entities["organizations"]:
        entity_parts.append(f"Organizations: {', '.join(entities['organizations'])}")
    if entities["people"]:
        entity_parts.append(f"Persons: {', '.join(entities['people'])}")
    if entities["numerics"]:
        entity_parts.append(f"Numerics: {', '.join(entities['numerics'][:4])}")

    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="text",
        engine="entity_extractor",
        indicator="typed_entities_extracted",
        description="Extracted typed entities: " + ("; ".join(entity_parts) if entity_parts else "No specific typed forensic entities identified."),
        location=EvidenceLocation(),
        model_score=None,
        confidence_band="high" if (entities["locations"] or entities["dates"]) else "medium",
        limitations=[
            "Entity extraction uses deterministic gazetteer validation and typed rules",
            "Complex slang, metaphors, or unlisted geographic locations may be omitted"
        ]
    ))

    # 3. Reference Context Comparison (Typed Matching Only)
    if reference_context and reference_context.strip():
        ref_text = reference_context.strip()
        ref_entities = extract_typed_entities(ref_text)

        # Lexical Jaccard Overlap
        doc_words = set(w.lower() for w in words)
        ref_words = set(w.lower() for w in re.findall(r'\b\w+\b', ref_text))
        intersection = doc_words.intersection(ref_words)
        union = doc_words.union(ref_words)
        jaccard = len(intersection) / len(union) if union else 0.0

        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="text",
            engine="text_reference_comparator",
            indicator="lexical_overlap_similarity",
            description=f"Lexical overlap against reference baseline: Jaccard similarity={jaccard:.2f} ({len(intersection)} shared vocabulary tokens).",
            location=EvidenceLocation(),
            model_score=round(jaccard, 3),
            confidence_band="high",
            limitations=[
                "Word overlap measures vocabulary reuse, not semantic validity",
                "Synonymous claims with different words yield lower lexical overlap"
            ]
        ))

        # --- Strict Typed Attribute Comparisons ---
        
        # A. Location <-> Location Comparison ONLY
        t_locs = {l.lower(): l for l in entities["locations"]}
        r_locs = {l.lower(): l for l in ref_entities["locations"]}
        
        if t_locs and r_locs:
            common_locs = set(t_locs.keys()).intersection(set(r_locs.keys()))
            diff_text = [t_locs[k] for k in set(t_locs.keys()) - set(r_locs.keys())]
            diff_ref = [r_locs[k] for k in set(r_locs.keys()) - set(t_locs.keys())]

            if diff_text and diff_ref:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_contradiction_engine",
                    indicator="location_mismatch_detected",
                    description=(
                        f"Location contradiction: Text evidence states location '{', '.join(diff_text)}' "
                        f"whereas reference baseline states '{', '.join(diff_ref)}'. "
                        f"Typed attribute comparison: Location ↔ Location conflict."
                    ),
                    location=EvidenceLocation(),
                    model_score=0.90,
                    confidence_band="high",
                    limitations=[
                        "Evaluated via typed location gazetteer comparison",
                        "Does not independently verify whether multiple sub-events occurred at distinct venues"
                    ]
                ))
            elif common_locs:
                matched_names = [t_locs[k] for k in common_locs]
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_corroboration_engine",
                    indicator="location_concordance",
                    description=f"Geographic corroboration: Both text evidence and reference context confirm location '{', '.join(matched_names)}'.",
                    location=EvidenceLocation(),
                    model_score=0.95,
                    confidence_band="high",
                    limitations=["Corroborates location mention; does not prove overall truthfulness of claims"]
                ))

        # B. Date <-> Date Comparison ONLY
        t_dates = {d.lower(): d for d in entities["dates"]}
        r_dates = {d.lower(): d for d in ref_entities["dates"]}
        
        if t_dates and r_dates:
            common_dates = set(t_dates.keys()).intersection(set(r_dates.keys()))
            diff_td = [t_dates[k] for k in set(t_dates.keys()) - set(r_dates.keys())]
            diff_rd = [r_dates[k] for k in set(r_dates.keys()) - set(t_dates.keys())]

            if diff_td and diff_rd:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_contradiction_engine",
                    indicator="temporal_mismatch_detected",
                    description=(
                        f"Date contradiction: Text evidence reports date '{', '.join(diff_td)}' "
                        f"while reference context reports '{', '.join(diff_rd)}'. "
                        f"Typed attribute comparison: Date ↔ Date conflict."
                    ),
                    location=EvidenceLocation(),
                    model_score=0.88,
                    confidence_band="high",
                    limitations=["Evaluated via calendar date and weekday token matching"]
                ))
            elif common_dates:
                matched_dates = [t_dates[k] for k in common_dates]
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="text",
                    engine="claim_corroboration_engine",
                    indicator="temporal_concordance",
                    description=f"Temporal corroboration: Both text evidence and reference context confirm date '{', '.join(matched_dates)}'.",
                    location=EvidenceLocation(),
                    model_score=0.92,
                    confidence_band="high",
                    limitations=["Corroborates stated date"]
                ))

        # 4. Optional AI Semantic Claim Comparison (if AI provider passed)
        if ai_helper:
            p_inst, api_key, model = ai_helper
            if p_inst and api_key:
                try:
                    ai_comparisons = p_inst.compare_claims(content, ref_text, api_key, model)
                    for comp in ai_comparisons:
                        verdict = comp.get("verdict", "RELATED")
                        findings.append(Finding(
                            finding_id=str(uuid.uuid4()),
                            evidence_id=evidence_id,
                            media_type="text",
                            engine=f"ai_semantic_{p_inst.provider_id}",
                            indicator=f"ai_{verdict.lower()}_analysis",
                            description=(
                                f"AI-assisted semantic evaluation ({p_inst.provider_name} {model}): "
                                f"{comp.get('explanation', '')} "
                                f"[Evidence: \"{comp.get('evidence_claim', '')}\" vs Reference: \"{comp.get('reference_claim', '')}\"]"
                            ),
                            location=EvidenceLocation(),
                            model_score=0.85 if verdict == "CONTRADICTS" else 0.75,
                            confidence_band=comp.get("confidence", "medium"),
                            limitations=[
                                f"AI-generated interpretation using {p_inst.provider_name}",
                                "Language model interpretations require human verification and are not legal forensic proof"
                            ]
                        ))
                except Exception as e:
                    print(f"AI claim comparison notice: {e}")

    return findings
