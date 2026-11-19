import re
from backend.schemas import Finding

KNOWN_LOCATIONS = {
    "bangalore", "bengaluru", "chennai", "mumbai", "delhi", "new delhi", "kolkata",
    "hyderabad", "pune", "ahmedabad", "jaipur", "london", "paris", "tokyo",
    "new york", "washington", "los angeles", "berlin", "san francisco", "chicago",
    "singapore", "dubai", "sydney", "geneva", "beijing", "seoul", "kyiv", "moscow"
}

DAYS_OF_WEEK = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"}

def extract_dates_from_text(text: str) -> list[str]:
    dates = []
    iso = re.findall(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', text)
    uk = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
    dates.extend(iso)
    dates.extend(uk)
    
    # EXIF format like 2024:05:12 14:30:00
    exif_dt = re.findall(r'\b\d{4}:\d{2}:\d{2}\b', text)
    dates.extend(exif_dt)

    t_lower = text.lower()
    for day in DAYS_OF_WEEK:
        if re.search(r'\b' + day + r'\b', t_lower):
            dates.append(day.capitalize())

    for m in MONTHS:
        matches = re.findall(r'\b' + m + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b', t_lower)
        if matches:
            dates.extend([match.title() for match in matches])
            
    return list(set(dates))

def extract_locations_from_text(text: str) -> list[str]:
    locations = []
    prep_matches = re.findall(r'\b(?:in|at|from|near|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
    for loc in prep_matches:
        locations.append(loc.title())
        
    t_lower = text.lower()
    for loc in KNOWN_LOCATIONS:
        if re.search(r'\b' + loc + r'\b', t_lower):
            locations.append(loc.title())
            
    return list(dict.fromkeys(locations))

def extract_named_entities_from_text(text: str) -> list[str]:
    # Proper noun phrases
    phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    filtered = [
        p for p in phrases 
        if not any(d in p for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Error Level", "Audio Amplitude", "Mel Spectrogram", "Color Channel"])
    ]
    return list(set(filtered))

def normalize_finding(finding: Finding) -> dict:
    """Extract standardized features from finding description and metadata."""
    desc = finding.description
    words = set(w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', desc))
    # Exclude common stopwords
    stopwords = {"and", "the", "for", "with", "from", "that", "this", "were", "been", "have", "analysis", "finding", "detected", "observed", "completed"}
    meaningful_words = words - stopwords
    
    return {
        "finding_id": finding.finding_id,
        "evidence_id": finding.evidence_id,
        "media_type": finding.media_type,
        "engine": finding.engine,
        "indicator": finding.indicator,
        "timestamp": finding.location.timestamp if finding.location else None,
        "frame_number": finding.location.frame_number if finding.location else None,
        "dates": extract_dates_from_text(desc),
        "locations": extract_locations_from_text(desc),
        "entities": extract_named_entities_from_text(desc),
        "words": meaningful_words,
        "confidence_band": finding.confidence_band,
        "model_score": finding.model_score,
        "raw": finding
    }
