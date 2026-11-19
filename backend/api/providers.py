from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import (
    AIProviderConfigResponse, AIProviderUpdateRequest,
    AIProviderTestResponse
)
from backend.ai.provider_manager import (
    list_providers, update_provider_config, delete_provider_key,
    test_provider_connection, get_provider_instance
)

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

SUPPORTED_PROVIDERS = {"gemini", "openai", "anthropic", "huggingface"}

@router.get("", response_model=list[AIProviderConfigResponse])
def get_all_providers(db: Session = Depends(get_db)):
    """Retrieve all configured AI providers with masked credentials."""
    return list_providers(db)

@router.get("/status")
def get_providers_status(db: Session = Depends(get_db)):
    """Get high-level status summary for all providers."""
    providers = list_providers(db)
    return {
        p["id"]: {
            "name": p["provider_name"],
            "configured": p["has_key"],
            "enabled": p["is_enabled"],
            "status": p["connection_status"],
            "selected_model": p["selected_model"]
        }
        for p in providers
    }

@router.post("/{provider}/configure")
def configure_provider(
    provider: str,
    payload: AIProviderUpdateRequest,
    db: Session = Depends(get_db)
):
    """Save API key, toggle status, or select default model."""
    p_id = provider.lower()
    if p_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}")
    res = update_provider_config(
        db=db,
        provider_id=p_id,
        api_key=payload.api_key,
        is_enabled=payload.is_enabled,
        selected_model=payload.selected_model
    )
    return {"status": "configured", "provider": p_id, "providers": res}

@router.post("/{provider}/test", response_model=AIProviderTestResponse)
def test_provider_endpoint(provider: str, db: Session = Depends(get_db)):
    """Test connection using stored encrypted credential."""
    p_id = provider.lower()
    if p_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")
    return test_provider_connection(db, p_id)

@router.delete("/{provider}")
def delete_provider_endpoint(provider: str, db: Session = Depends(get_db)):
    """Delete encrypted key and disable provider."""
    p_id = provider.lower()
    if p_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")
    delete_provider_key(db, p_id)
    return {"status": "deleted", "provider": p_id}

@router.get("/{provider}/models")
def get_provider_models(provider: str):
    """Retrieve list of supported models for a provider."""
    p_id = provider.lower()
    inst = get_provider_instance(p_id)
    if not inst:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found.")
    models = getattr(inst, "supported_models", getattr(inst, "available_models", []))
    default_m = getattr(inst, "default_model", models[0] if models else "")
    return {
        "provider": p_id,
        "default_model": default_m,
        "supported_models": models
    }
