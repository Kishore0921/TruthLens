from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import AIProviderConfig, AIUsageLog
from backend.ai.secret_manager import encrypt_secret, decrypt_secret, mask_secret
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.openai_provider import OpenAIProvider
from backend.ai.anthropic_provider import AnthropicProvider
from backend.ai.huggingface_provider import HuggingFaceProvider

_PROVIDERS = {
    "gemini": GeminiProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "huggingface": HuggingFaceProvider(),
}

def get_provider_instance(provider_id: str):
    return _PROVIDERS.get(provider_id.lower())

def list_providers(db: Session) -> list[dict]:
    configs = db.query(AIProviderConfig).all()
    results = []
    for c in configs:
        p_inst = get_provider_instance(c.id)
        has_key = bool(c.encrypted_api_key and len(c.encrypted_api_key) > 5)
        raw_key = ""
        if has_key:
            try:
                raw_key = decrypt_secret(c.encrypted_api_key)
            except Exception:
                raw_key = ""
                
        results.append({
            "id": c.id,
            "provider_name": c.provider_name,
            "has_key": has_key,
            "masked_key": mask_secret(raw_key) if raw_key else "",
            "is_enabled": bool(c.is_enabled),
            "selected_model": c.selected_model or (p_inst.available_models[0] if p_inst else ""),
            "connection_status": c.connection_status,
            "last_tested_at": c.last_tested_at,
            "last_error": c.last_error,
            "available_models": p_inst.available_models if p_inst else []
        })
    return results

def update_provider_config(
    db: Session,
    provider_id: str,
    api_key: str | None = None,
    is_enabled: bool | None = None,
    selected_model: str | None = None
) -> dict:
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not cfg:
        p_inst = get_provider_instance(provider_id)
        name = p_inst.provider_name if p_inst else provider_id.capitalize()
        cfg = AIProviderConfig(id=provider_id, provider_name=name)
        db.add(cfg)

    if api_key is not None:
        key_stripped = api_key.strip()
        if key_stripped:
            cfg.encrypted_api_key = encrypt_secret(key_stripped)
            cfg.connection_status = "configured"
        else:
            cfg.encrypted_api_key = ""
            cfg.connection_status = "not_configured"

    if is_enabled is not None:
        cfg.is_enabled = is_enabled

    if selected_model is not None:
        cfg.selected_model = selected_model

    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cfg)

    # Return safe masked representation
    return list_providers(db)

def delete_provider_key(db: Session, provider_id: str):
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if cfg:
        cfg.encrypted_api_key = ""
        cfg.connection_status = "not_configured"
        cfg.last_error = None
        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()

def test_provider_connection(db: Session, provider_id: str) -> dict:
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not cfg or not cfg.encrypted_api_key:
        return {
            "provider": provider_id,
            "success": False,
            "status": "not_configured",
            "message": "No API key configured for this provider."
        }

    p_inst = get_provider_instance(provider_id)
    if not p_inst:
        return {
            "provider": provider_id,
            "success": False,
            "status": "connection_failed",
            "message": f"Provider {provider_id} is not supported."
        }

    try:
        raw_key = decrypt_secret(cfg.encrypted_api_key)
        success, msg = p_inst.test_connection(raw_key, cfg.selected_model)
        cfg.last_tested_at = datetime.now(timezone.utc)
        if success:
            cfg.connection_status = "connection_successful"
            cfg.last_error = None
        else:
            cfg.connection_status = "connection_failed"
            cfg.last_error = msg
        db.commit()
        return {
            "provider": provider_id,
            "success": success,
            "status": cfg.connection_status,
            "message": msg,
            "model_used": cfg.selected_model
        }
    except Exception as e:
        cfg.connection_status = "connection_failed"
        cfg.last_error = str(e)
        db.commit()
        return {
            "provider": provider_id,
            "success": False,
            "status": "connection_failed",
            "message": str(e)
        }

def get_active_provider_and_key(db: Session, provider_id: str) -> tuple[Any, str, str]:
    """Internal helper: returns (provider_instance, decrypted_api_key, model_name)."""
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not cfg or not cfg.is_enabled or not cfg.encrypted_api_key:
        return None, "", ""
    try:
        raw_key = decrypt_secret(cfg.encrypted_api_key)
        p_inst = get_provider_instance(provider_id)
        return p_inst, raw_key, cfg.selected_model or ""
    except Exception:
        return None, "", ""
