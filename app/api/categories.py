"""
API endpoints for categories
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.category import Category
from app.services.neo4j_service import neo4j_service
from pydantic import BaseModel

router = APIRouter()


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    element_count: int
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    try:
        # Ensure tables exist
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        categories = db.query(Category).all()
        return categories
    except Exception as e:
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

