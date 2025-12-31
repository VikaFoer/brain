"""
API endpoints for system status
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.category import Category
from app.models.legal_act import LegalAct
from app.core.config import settings
from app.core.neo4j_db import neo4j_driver

router = APIRouter()


@router.get("/")
async def get_status(db: Session = Depends(get_db)):
    """Get system status and statistics"""
    try:
        # Check if database is accessible
        from sqlalchemy import inspect, text
        from app.core.database import engine
        
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
        
        return {
            "status": "online",
            "database": {
                "type": "sqlite" if "sqlite" in str(settings.DATABASE_URL) else "postgresql",
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
