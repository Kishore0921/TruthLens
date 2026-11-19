from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import (
    AIProviderConfigResponse, AIProviderUpdateRequest,
    AIProviderTestResponse, ReferenceExtractionRequest, ReferenceExtractionResponse
)
from backend.ai.provider_manager import (
    list_providers, update_provider_config, delete_provider_key,
    test_provider_connection, get_active_provider_and_key
)
from backend.engines.text_engine import extract_typed_entities

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

@router.get("/providers", response_model=list[AIProviderConfigResponse])
@router.get("/ai-providers", response_model=list[AIProviderConfigResponse])
def get_providers(db: Session = Depends(get_db)):
    """Retrieve configured AI providers with masked credentials."""
    return list_providers(db)

@router.put("/providers/{provider_id}")
@router.put("/ai-providers/{provider_id}")
def update_provider(
    provider_id: str,
    payload: AIProviderUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update provider settings and/or encrypt and save API key."""
    if provider_id not in ["gemini", "openai", "anthropic", "huggingface"]:
        raise HTTPException(status_code=400, detail="Unsupported AI provider.")
    res = update_provider_config(
        db=db,
        provider_id=provider_id,
        api_key=payload.api_key,
        is_enabled=payload.is_enabled,
        selected_model=payload.selected_model
    )
    return {"status": "updated", "providers": res}

@router.delete("/providers/{provider_id}")
@router.delete("/ai-providers/{provider_id}")
@router.delete("/ai-providers/{provider_id}/key")
def remove_provider_key(provider_id: str, db: Session = Depends(get_db)):
    """Securely remove encrypted key for a provider."""
    delete_provider_key(db, provider_id)
    return {"status": "cleared", "provider": provider_id}

@router.post("/providers/{provider_id}/test", response_model=AIProviderTestResponse)
@router.post("/ai-providers/{provider_id}/test", response_model=AIProviderTestResponse)
def test_provider(provider_id: str, db: Session = Depends(get_db)):
    """Test connection using stored encrypted credential."""
    res = test_provider_connection(db, provider_id)
    return res

@router.post("/extract-reference-facts", response_model=ReferenceExtractionResponse)
def extract_reference_facts(payload: ReferenceExtractionRequest, db: Session = Depends(get_db)):
    """
    Extract structured facts from reference context.
    Uses AI provider if configured and enabled, otherwise falls back to deterministic rule extraction.
    """
    text = payload.text.strip()
    if not text:
        return ReferenceExtractionResponse()

    # Try AI provider first if enabled
    ai_extracted = None
    for p_id in ["gemini", "openai"]:
        p_inst, api_key, model = get_active_provider_and_key(db, p_id)
        if p_inst and api_key:
            try:
                ai_data = p_inst.extract_structured_facts(text, api_key, model)
                if ai_data and isinstance(ai_data, dict):
                    ai_extracted = ai_data
                    break
            except Exception:
                pass

    if ai_extracted:
        return ReferenceExtractionResponse(
            event_date=ai_extracted.get("event_date", ""),
            event_time=ai_extracted.get("event_time", ""),
            location=ai_extracted.get("location", ""),
            people=ai_extracted.get("people", []) if isinstance(ai_extracted.get("people"), list) else [],
            organizations=ai_extracted.get("organizations", []) if isinstance(ai_extracted.get("organizations"), list) else [],
            event_type=ai_extracted.get("event_type", ""),
            important_claims=ai_extracted.get("important_claims", []) if isinstance(ai_extracted.get("important_claims"), list) else []
        )

    # Deterministic fallback extraction
    typed = extract_typed_entities(text)
    primary_loc = typed["locations"][0] if typed["locations"] else ""
    primary_date = typed["dates"][0] if typed["dates"] else ""
    primary_time = typed["times"][0] if typed["times"] else ""
    
    return ReferenceExtractionResponse(
        event_date=primary_date,
        event_time=primary_time,
        location=primary_loc,
        people=typed.get("people", []),
        organizations=typed.get("organizations", []),
        event_type="general_event",
        important_claims=[f"Incident recorded in {primary_loc}"] if primary_loc else []
    )
