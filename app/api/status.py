"""
API endpoints for system status
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, engine
from app.models.category import Category
from app.models.legal_act import LegalAct
from app.core.config import settings
from app.core.neo4j_db import neo4j_driver

router = APIRouter()


@router.get("/")
async def get_status(db: Session = Depends(get_db)):
    """Get system status including database connection"""
    try:
        # Check if database is accessible
        from sqlalchemy import inspect, text
        
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            tables_exist = "categories" in tables
        except Exception as db_error:
            return {
                "status": "database_error",
                "message": f"Database connection error: {str(db_error)}",
                "database": {
                    "accessible": False,
                    "error": str(db_error)
                },
                "recommendation": "Add PostgreSQL service in Railway or set DATABASE_URL environment variable"
            }
        
        if not tables_exist:
            return {
                "status": "database_not_initialized",
                "message": "Database tables not created. Tables will be created automatically on next request.",
                "database": {
                    "tables_exist": False,
                    "accessible": True
                }
            }
        
        categories_count = db.query(Category).count()
        acts_count = db.query(LegalAct).count()
        
        # Check Neo4j
        neo4j_status = "not_configured"
        if settings.NEO4J_PASSWORD:
            try:
                if neo4j_driver.verify_connectivity():
                    neo4j_status = "connected"
                else:
                    neo4j_status = "disconnected"
            except:
                neo4j_status = "error"
        
        # Determine database type
        database_url = settings.DATABASE_URL or "sqlite:///./legal_db.db"
        
        # Check if DATABASE_URL is actually set (not just default)
        url_is_set = bool(settings.DATABASE_URL)
        
        # Check if it's a Railway Reference (starts with ${{)
        is_reference = database_url.startswith("${{") if database_url else False
        
        # If it's a reference, it means Railway hasn't resolved it yet
        if is_reference:
            db_type = "reference_not_resolved"
            db_connected = False
            db_url_preview = "Reference not resolved by Railway"
        else:
            is_sqlite = database_url.startswith("sqlite")
            db_type = "sqlite" if is_sqlite else "postgresql"
            
            # Show preview of DATABASE_URL (hide password)
            db_url_preview = None
            db_connected = True
            if database_url and not is_sqlite:
                # Hide password in preview
                try:
                    from urllib.parse import urlparse, urlunparse
                    parsed = urlparse(database_url)
                    if parsed.password:
                        # Replace password with ***
                        netloc = f"{parsed.username}:***@{parsed.hostname}"
                        if parsed.port:
                            netloc += f":{parsed.port}"
                        safe_parsed = parsed._replace(netloc=netloc)
                        db_url_preview = urlunparse(safe_parsed)
                    else:
                        db_url_preview = database_url[:50] + "..." if len(database_url) > 50 else database_url
                except:
                    db_url_preview = "postgresql://***"
            
            # Check if DATABASE_URL is set (for PostgreSQL)
            if not url_is_set or database_url == "sqlite:///./legal_db.db":
                db_connected = False
                db_type = "not_configured"
        
        return {
            "status": "online",
            "database": {
                "type": db_type,
                "connected": db_connected,
                "tables_exist": tables_exist,
                "url_preview": db_url_preview,
                "url_set": url_is_set and not is_reference,
                "url_is_reference": is_reference,
                "categories_count": categories_count,
                "legal_acts_count": acts_count,
                "initialized": categories_count > 0
            },
            "neo4j": {
                "status": neo4j_status,
                "configured": bool(settings.NEO4J_PASSWORD)
            },
            "openai": {
                "configured": bool(settings.OPENAI_API_KEY),
                "model": settings.OPENAI_MODEL
            },
            "rada_api": {
                "configured": bool(settings.RADA_API_TOKEN),
                "base_url": settings.RADA_API_BASE_URL
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
