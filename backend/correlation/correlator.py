from backend.schemas import Finding, CorrelationResult
from backend.correlation.rules import apply_all_rules

async def correlate_findings(findings: list[Finding], reference_context: str = "") -> list[CorrelationResult]:
    """Correlate findings across multiple evidence types and reference context."""
    if len(findings) < 2:
        return []
    return apply_all_rules(findings, reference_context)
