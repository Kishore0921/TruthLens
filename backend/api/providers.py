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
from backend.models_registry import ModelRegistry
from backend.ai.datasets_manager import list_forensic_datasets, get_dataset_info
from backend.config import EXECUTION_MODE

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

SUPPORTED_PROVIDERS = {"gemini", "openai", "anthropic", "huggingface"}

@router.get("", response_model=list[AIProviderConfigResponse])
def get_all_providers(db: Session = Depends(get_db)):
    """Retrieve all configured AI providers with masked credentials loaded from backend/.env."""
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
            "selected_model": p["selected_model"],
            "config_source": p.get("config_source", "backend/.env")
        }
        for p in providers
    }

@router.post("/{provider}/configure")
def configure_provider(
    provider: str,
    payload: AIProviderUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update runtime settings (model selection, enabled toggle).
    API keys cannot be submitted via API; they are managed in backend/.env.
    """
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
    """Test connection using credentials loaded from backend/.env."""
    p_id = provider.lower()
    if p_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")
    return test_provider_connection(db, p_id)

@router.delete("/{provider}")
def delete_provider_endpoint(provider: str, db: Session = Depends(get_db)):
    """Disable provider in TruthLens."""
    p_id = provider.lower()
    if p_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")
    delete_provider_key(db, p_id)
    return {"status": "disabled", "provider": p_id}

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

@router.get("/system/health")
def get_system_ai_health(db: Session = Depends(get_db)):
    """
    Comprehensive diagnostics endpoint:
    - Execution mode (HYBRID, LOCAL, CLOUD)
    - Configured providers from backend/.env
    - Local & Hugging Face model registry status
    - System hardware capabilities
    """
    import os
    providers = list_providers(db)
    models = ModelRegistry.get_instance().list_models()
    
    return {
        "execution_mode": EXECUTION_MODE,
        "env_file_location": "backend/.env",
        "providers": {
            p["id"]: {
                "name": p["provider_name"],
                "configured": p["has_key"],
                "enabled": p["is_enabled"],
                "status": p["connection_status"],
                "selected_model": p["selected_model"]
            }
            for p in providers
        },
        "models": models,
        "hardware": {
            "device": "cpu",
            "cpu_cores": os.cpu_count() or 2,
            "architecture": "x86_64 CPU-First",
            "max_image_dim": 512,
            "max_video_frames": 10,
            "max_audio_duration_s": 15.0
        }
    }

@router.get("/datasets/catalog")
def get_forensic_datasets_catalog():
    """Retrieve catalog of curated Hugging Face forensic evaluation benchmark datasets."""
    return list_forensic_datasets()

@router.get("/datasets/{dataset_id}")
def get_forensic_dataset_details(dataset_id: str):
    """Retrieve metadata for a specific benchmark dataset without downloading full weights."""
    info = get_dataset_info(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found in catalog.")
    return info
