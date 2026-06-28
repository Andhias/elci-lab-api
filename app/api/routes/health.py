from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@router.get("/debug/config", tags=["system"])
def debug_config() -> dict:
    key = settings.openai_compatible_api_key
    return {
        "llm_provider": settings.llm_provider,
        "base_url": settings.openai_compatible_base_url,
        "model": settings.openai_compatible_model,
        "key_len": len(key),
        "key_prefix": key[:10] + "..." if key else "EMPTY",
    }
