"""
API endpoints for legal acts
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.legal_act import LegalAct
from app.models.category import Category
from app.services.processing_service import ProcessingService
from pydantic import BaseModel

router = APIRouter()


class LegalActResponse(BaseModel):
    id: int
    nreg: str
    title: str
    is_processed: bool
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[LegalActResponse])
async def get_legal_acts(
    skip: int = 0,
    limit: int = 100,
    processed_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get legal acts"""
    query = db.query(LegalAct)
    
    if processed_only:
        query = query.filter(LegalAct.is_processed == True)
    
    acts = query.offset(skip).limit(limit).all()
    return acts


@router.get("/{nreg}", response_model=LegalActResponse)
async def get_legal_act(nreg: str, db: Session = Depends(get_db)):
    """Get legal act by nreg"""
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if not act:
        raise HTTPException(status_code=404, detail="Legal act not found")
    return act


@router.post("/{nreg}/process")
async def process_legal_act(
    nreg: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process a legal act (download, extract elements, sync to DBs)"""
    from app.core.database import SessionLocal
    import asyncio
    
    async def process():
        # Create new session for background task
        bg_db = SessionLocal()
        try:
            bg_service = ProcessingService(bg_db)
            await bg_service.process_legal_act(nreg)
        finally:
            bg_db.close()
    
    background_tasks.add_task(lambda: asyncio.run(process()))
    
    return {"message": f"Processing started for {nreg}"}


@router.post("/initialize-categories")
async def initialize_categories(db: Session = Depends(get_db)):
    """Initialize categories in database"""
    try:
        # Ensure tables exist first
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        processing_service = ProcessingService(db)
        await processing_service.initialize_categories()
        
        count = db.query(Category).count()
        return {
            "message": "Categories initialized successfully",
            "count": count,
            "status": "success"
        }
    except Exception as e:
        error_msg = str(e)
        # Provide helpful error message
        if "no such table" in error_msg.lower() or "relation" in error_msg.lower():
            error_msg += ". Tables should be created automatically. Please check DATABASE_URL."
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing categories: {error_msg}"
        )
