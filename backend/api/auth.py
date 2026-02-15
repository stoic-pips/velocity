"""
Dunam Velocity – API Key Authentication
FastAPI dependency that validates the X-API-Key header on every request.
"""

from fastapi import Header, HTTPException, status

from config.settings import get_settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    FastAPI dependency: reads X-API-Key header and compares against config.
    Raises 401 if missing or invalid.
    """
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized – invalid or missing API key",
        )
    return x_api_key
