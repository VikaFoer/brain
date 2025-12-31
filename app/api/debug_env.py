"""
Debug endpoint to check environment variables (тільки для діагностики)
"""
from fastapi import APIRouter
import os
from app.core.config import settings

router = APIRouter()


@router.get("/debug/env")
async def debug_env():
    """
    Debug endpoint to see what environment variables are available
    WARNING: This exposes sensitive information - remove in production!
    """
    # Get DATABASE_URL from environment directly
    db_url_env = os.getenv("DATABASE_URL", "NOT_SET")
    db_url_settings = settings.DATABASE_URL
    
    # Check if it's a Railway Reference
    is_reference = db_url_env.startswith("${{") if db_url_env else False
    
    return {
        "DATABASE_URL_from_env": db_url_env[:100] + "..." if len(db_url_env) > 100 else db_url_env,
        "DATABASE_URL_from_settings": str(db_url_settings)[:100] + "..." if db_url_settings and len(str(db_url_settings)) > 100 else str(db_url_settings),
        "is_reference": is_reference,
        "env_length": len(db_url_env) if db_url_env else 0,
        "settings_is_none": db_url_settings is None,
        "all_env_vars_with_db": {
            k: (v[:50] + "..." if len(v) > 50 else v) 
            for k, v in os.environ.items() 
            if "DATABASE" in k or "POSTGRES" in k
        }
    }

