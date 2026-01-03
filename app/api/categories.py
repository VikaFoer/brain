"""
API endpoints for categories
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging
from app.core.database import get_db
from app.models.category import Category
from app.services.neo4j_service import neo4j_service
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class CategoryResponse(BaseModel):
    id: int
    name: str
    code: int | None = None  # Код класифікації (може бути None для старих записів)
    description: str | None = None
    element_count: int = 0
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    try:
        # Ensure tables exist
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        # Try to add code column if it doesn't exist (for existing databases)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('categories')]
            if 'code' not in columns:
                logger.warning("Column 'code' not found in categories table, adding it...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE categories ADD COLUMN code INTEGER"))
                    conn.commit()
                logger.info("Column 'code' added successfully")
        except Exception as migration_error:
            # Column might already exist or migration failed, continue
            logger.debug(f"Migration check: {migration_error}")
        
        categories = db.query(Category).all()
        return categories
    except Exception as e:
        logger.error(f"Error getting categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}. Please ensure DATABASE_URL is set correctly."
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/{category_id}/statistics")
async def get_category_statistics(category_id: int, db: Session = Depends(get_db)):
    """Get statistics for a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get from Neo4j
    stats = neo4j_service.get_category_statistics()
    category_stats = next((s for s in stats if s["id"] == category_id), None)
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "element_count": category.element_count
        },
        "statistics": category_stats
    }

