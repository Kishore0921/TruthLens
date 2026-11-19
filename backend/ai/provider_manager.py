from typing import Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models import AIProviderConfig, AIUsageLog
from backend.ai.secret_manager import mask_secret
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.openai_provider import OpenAIProvider
from backend.ai.anthropic_provider import AnthropicProvider
from backend.ai.huggingface_provider import HuggingFaceProvider
from backend.config import (
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, HF_TOKEN,
    GEMINI_DEFAULT_MODEL, OPENAI_DEFAULT_MODEL, ANTHROPIC_DEFAULT_MODEL, HF_DEFAULT_MODEL,
    EXECUTION_MODE
)

_PROVIDERS = {
    "gemini": GeminiProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "huggingface": HuggingFaceProvider(),
}

def get_env_credentials_map() -> dict[str, dict[str, str]]:
    """Mapping of provider ID to its environment variables and default models."""
    return {
        "gemini": {
            "key": GEMINI_API_KEY,
            "default_model": GEMINI_DEFAULT_MODEL,
            "name": "Google Gemini"
        },
        "openai": {
            "key": OPENAI_API_KEY,
            "default_model": OPENAI_DEFAULT_MODEL,
            "name": "OpenAI"
        },
        "anthropic": {
            "key": ANTHROPIC_API_KEY,
            "default_model": ANTHROPIC_DEFAULT_MODEL,
            "name": "Anthropic Claude"
        },
        "huggingface": {
            "key": HF_TOKEN,
            "default_model": HF_DEFAULT_MODEL,
            "name": "Hugging Face"
        }
    }

def get_provider_instance(provider_id: str):
    return _PROVIDERS.get(provider_id.lower())

def sync_env_providers_with_db(db: Session):
    """
    Ensure the DB has a record for every supported provider,
    reflecting configuration state from backend/.env without exposing keys.
    """
    env_map = get_env_credentials_map()
    for p_id, p_info in env_map.items():
        cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == p_id).first()
        if not cfg:
            cfg = AIProviderConfig(
                id=p_id,
                provider_name=p_info["name"],
                selected_model=p_info["default_model"],
                is_enabled=bool(p_info["key"]) and (EXECUTION_MODE != "LOCAL"),
                connection_status="configured" if p_info["key"] else "not_configured"
            )
            db.add(cfg)
        else:
            if p_info["key"] and cfg.connection_status == "not_configured":
                cfg.connection_status = "configured"
            elif not p_info["key"]:
                cfg.connection_status = "not_configured"
                cfg.is_enabled = False
    try:
        db.commit()
    except Exception:
        db.rollback()

def list_providers(db: Session) -> list[dict]:
    sync_env_providers_with_db(db)
    configs = db.query(AIProviderConfig).all()
    env_map = get_env_credentials_map()
    results = []
    
    for c in configs:
        p_inst = get_provider_instance(c.id)
        p_info = env_map.get(c.id, {})
        env_key = p_info.get("key", "")
        has_key = bool(env_key)

        models = getattr(p_inst, "supported_models", getattr(p_inst, "available_models", [])) if p_inst else []
        selected = c.selected_model or p_info.get("default_model", models[0] if models else "")
        
        results.append({
            "id": c.id,
            "provider_name": c.provider_name,
            "has_key": has_key,
            "masked_key": mask_secret(env_key) if has_key else "",
            "is_enabled": bool(c.is_enabled) and has_key and (EXECUTION_MODE != "LOCAL"),
            "selected_model": selected,
            "connection_status": c.connection_status if has_key else "not_configured",
            "last_tested_at": c.last_tested_at,
            "last_error": c.last_error,
            "available_models": models,
            "config_source": "backend/.env" if has_key else "missing_in_env",
            "execution_mode": EXECUTION_MODE
        })
    return results

def update_provider_config(
    db: Session,
    provider_id: str,
    api_key: str | None = None,
    is_enabled: bool | None = None,
    selected_model: str | None = None
) -> list[dict]:
    """
    Update runtime settings (model selection and toggle enabled).
    Does NOT accept API key from client; credentials must reside in backend/.env.
    """
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    env_map = get_env_credentials_map()
    p_info = env_map.get(provider_id, {})

    if not cfg:
        p_inst = get_provider_instance(provider_id)
        name = p_inst.provider_name if p_inst else provider_id.capitalize()
        cfg = AIProviderConfig(id=provider_id, provider_name=name)
        db.add(cfg)

    # Note: api_key parameter is ignored as credentials must be set in .env
    if is_enabled is not None:
        cfg.is_enabled = bool(is_enabled) and bool(p_info.get("key"))

    if selected_model is not None:
        cfg.selected_model = selected_model

    cfg.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cfg)
    return list_providers(db)

def delete_provider_key(db: Session, provider_id: str):
    """
    Disable provider in DB (actual credentials reside in backend/.env).
    """
    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if cfg:
        cfg.is_enabled = False
        cfg.connection_status = "not_configured"
        cfg.last_error = "Disabled by user. Remove key from backend/.env to permanently unconfigure."
        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()

def test_provider_connection(db: Session, provider_id: str) -> dict:
    env_map = get_env_credentials_map()
    p_info = env_map.get(provider_id)
    if not p_info or not p_info.get("key"):
        return {
            "provider": provider_id,
            "success": False,
            "status": "not_configured",
            "message": f"No credential found in backend/.env ({provider_id.upper()}_API_KEY is unset)."
        }

    p_inst = get_provider_instance(provider_id)
    if not p_inst:
        return {
            "provider": provider_id,
            "success": False,
            "status": "connection_failed",
            "message": f"Provider {provider_id} is not supported."
        }

    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    selected_model = cfg.selected_model if cfg and cfg.selected_model else p_info["default_model"]
    raw_key = p_info["key"]

    try:
        success, msg = p_inst.test_connection(raw_key, selected_model)
        if cfg:
            cfg.last_tested_at = datetime.now(timezone.utc)
            if success:
                cfg.connection_status = "connected"
                cfg.last_error = None
            else:
                cfg.connection_status = "error"
                cfg.last_error = msg
            db.commit()

        return {
            "provider": provider_id,
            "success": success,
            "status": "connected" if success else "error",
            "message": msg,
            "model_used": selected_model
        }
    except Exception as e:
        if cfg:
            cfg.connection_status = "error"
            cfg.last_error = str(e)
            db.commit()
        return {
            "provider": provider_id,
            "success": False,
            "status": "error",
            "message": str(e)
        }

def get_active_provider_and_key(db: Session, provider_id: str) -> tuple[Any, str, str]:
    """
    Internal helper: returns (provider_instance, api_key_from_env, selected_model).
    Returns (None, "", "") if execution mode is LOCAL, provider disabled, or key missing.
    """
    if EXECUTION_MODE == "LOCAL":
        return None, "", ""

    env_map = get_env_credentials_map()
    p_info = env_map.get(provider_id)
    if not p_info or not p_info.get("key"):
        return None, "", ""

    cfg = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if cfg and not cfg.is_enabled:
        return None, "", ""

    p_inst = get_provider_instance(provider_id)
    selected_model = cfg.selected_model if cfg and cfg.selected_model else p_info["default_model"]
    return p_inst, p_info["key"], selected_model
