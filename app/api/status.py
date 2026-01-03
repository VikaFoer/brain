"""
API endpoints for system status
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, inspect
from app.core.database import get_db, engine
from app.models.category import Category
from app.models.legal_act import LegalAct, ActCategory, ActRelation
from app.models.subset import Subset
from app.core.config import settings
from app.core.neo4j_db import neo4j_driver
from typing import Dict, Any

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


@router.get("/database-schema")
async def get_database_schema(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get detailed database schema and statistics"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Get table schemas
        table_schemas = {}
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            
            table_schemas[table_name] = {
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "default": str(col.get("default", ""))
                    }
                    for col in columns
                ],
                "foreign_keys": [
                    {
                        "name": fk["name"],
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    }
                    for fk in foreign_keys
                ],
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx["unique"]
                    }
                    for idx in indexes
                ]
            }
        
        # Get statistics for each table
        stats = {}
        for table_name in tables:
            try:
                if table_name == "categories":
                    stats[table_name] = {
                        "count": db.query(Category).count(),
                        "sample": [
                            {"id": c.id, "name": c.name, "element_count": c.element_count}
                            for c in db.query(Category).limit(5).all()
                        ]
                    }
                elif table_name == "legal_acts":
                    total = db.query(LegalAct).count()
                    processed = db.query(LegalAct).filter(LegalAct.is_processed == True).count()
                    stats[table_name] = {
                        "count": total,
                        "processed": processed,
                        "not_processed": total - processed,
                        "with_text": db.query(LegalAct).filter(LegalAct.text.isnot(None)).count(),
                        "with_embeddings": db.query(LegalAct).filter(LegalAct.embeddings.isnot(None)).count(),
                        "sample": [
                            {
                                "id": a.id,
                                "nreg": a.nreg,
                                "title": a.title[:100] + "..." if len(a.title) > 100 else a.title,
                                "is_processed": a.is_processed
                            }
                            for a in db.query(LegalAct).limit(5).all()
                        ]
                    }
                elif table_name == "subsets":
                    stats[table_name] = {
                        "count": db.query(Subset).count(),
                        "sample": [
                            {"id": s.id, "name": s.name, "category_id": s.category_id}
                            for s in db.query(Subset).limit(5).all()
                        ]
                    }
                elif table_name == "act_categories":
                    stats[table_name] = {
                        "count": db.query(ActCategory).count(),
                        "sample": [
                            {"id": ac.id, "act_id": ac.act_id, "category_id": ac.category_id, "confidence": ac.confidence}
                            for ac in db.query(ActCategory).limit(5).all()
                        ]
                    }
                elif table_name == "act_relations":
                    stats[table_name] = {
                        "count": db.query(ActRelation).count(),
                        "by_type": {
                            rel_type: db.query(ActRelation).filter(ActRelation.relation_type == rel_type).count()
                            for rel_type in db.query(ActRelation.relation_type).distinct().all()
                        },
                        "sample": [
                            {
                                "id": r.id,
                                "source_act_id": r.source_act_id,
                                "target_act_id": r.target_act_id,
                                "relation_type": r.relation_type
                            }
                            for r in db.query(ActRelation).limit(5).all()
                        ]
                    }
                else:
                    # Generic count for other tables
                    result = db.execute(f"SELECT COUNT(*) FROM {table_name}")
                    stats[table_name] = {
                        "count": result.scalar()
                    }
            except Exception as e:
                stats[table_name] = {
                    "error": str(e)
                }
        
        # Get relationships summary
        relationships = {
            "category_to_subset": db.query(Subset).count(),
            "subset_to_act": db.query(LegalAct).filter(LegalAct.subset_id.isnot(None)).count(),
            "act_to_category": db.query(ActCategory).count(),
            "act_to_act": db.query(ActRelation).count()
        }
        
        return {
            "tables": list(tables),
            "schemas": table_schemas,
            "statistics": stats,
            "relationships": relationships,
            "database_type": "postgresql" if "postgresql" in str(engine.url) else "sqlite"
        }
    except Exception as e:
        return {
            "error": str(e),
            "tables": [],
            "schemas": {},
            "statistics": {}
        }
