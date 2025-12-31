"""
API endpoints for legal acts
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from urllib.parse import unquote
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
    document_type: Optional[str] = None
    status: Optional[str] = None
    date_acceptance: Optional[str] = None
    date_publication: Optional[str] = None
    
    class Config:
        from_attributes = True


class LegalActDetailResponse(BaseModel):
    id: int
    nreg: str
    title: str
    is_processed: bool
    processed_at: Optional[str] = None
    document_type: Optional[str] = None
    status: Optional[str] = None
    date_acceptance: Optional[str] = None
    date_publication: Optional[str] = None
    extracted_elements: Optional[dict] = None
    extracted_relations: Optional[dict] = None
    categories: List[dict] = []
    
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
    
    acts = query.order_by(LegalAct.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to response format with proper date formatting
    result = []
    for act in acts:
        result.append(LegalActResponse(
            id=act.id,
            nreg=act.nreg,
            title=act.title,
            is_processed=act.is_processed,
            document_type=act.document_type,
            status=act.status,
            date_acceptance=act.date_acceptance.isoformat() if act.date_acceptance else None,
            date_publication=act.date_publication.isoformat() if act.date_publication else None
        ))
    return result


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


# IMPORTANT: Specific routes must come BEFORE the general {nreg:path} route
# Otherwise FastAPI will match /check, /details, /process as part of nreg

@router.get("/{nreg:path}/check")
async def check_legal_act_exists(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    db: Session = Depends(get_db)
):
    """Check if legal act exists on Rada website"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    
    from app.services.rada_api import rada_api
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if already in database
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if act:
        return {
            "exists": True,
            "in_database": True,
            "is_processed": act.is_processed,
            "title": act.title,
            "message": "Акт знайдено в базі даних"
        }
    
    # Check on Rada website
    try:
        logger.info(f"Checking act {nreg} on Rada website...")
        document_json = await rada_api.get_document_json(nreg)
        if document_json:
            title = document_json.get("title", nreg)
            logger.info(f"Act {nreg} found on Rada website: {title}")
            return {
                "exists": True,
                "in_database": False,
                "is_processed": False,
                "title": title,
                "message": f"Акт знайдено на сайті data.rada.gov.ua: {title}"
            }
        else:
            logger.warning(f"Act {nreg} not found on Rada website")
            # Try alternative formats
            alternative_nregs = [
                nreg.replace('/', '-'),
                nreg.replace('к', 'к/'),
                nreg.upper(),
                nreg.lower()
            ]
            
            for alt_nreg in alternative_nregs:
                if alt_nreg == nreg:
                    continue
                logger.info(f"Trying alternative format: {alt_nreg}")
                alt_doc = await rada_api.get_document_json(alt_nreg)
                if alt_doc:
                    title = alt_doc.get("title", alt_nreg)
                    return {
                        "exists": True,
                        "in_database": False,
                        "is_processed": False,
                        "title": title,
                        "message": f"Акт знайдено на сайті data.rada.gov.ua (альтернативний формат): {title}"
                    }
            
            return {
                "exists": False,
                "in_database": False,
                "is_processed": False,
                "title": None,
                "message": f"Акт {nreg} не знайдено на сайті data.rada.gov.ua. Перевірте правильність номера реєстрації."
            }
    except Exception as e:
        logger.error(f"Error checking act {nreg}: {e}", exc_info=True)
        return {
            "exists": False,
            "in_database": False,
            "is_processed": False,
            "title": None,
            "message": f"Помилка при перевірці акту: {str(e)}"
        }


@router.get("/{nreg:path}/details", response_model=LegalActDetailResponse)
async def get_legal_act_details(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    db: Session = Depends(get_db)
):
    """Get detailed information about processed legal act including extracted elements"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if not act:
        raise HTTPException(status_code=404, detail="Legal act not found")
    
    # Get categories
    categories = []
    for act_cat in act.categories:
        categories.append({
            "id": act_cat.category.id,
            "name": act_cat.category.name,
            "confidence": act_cat.confidence
        })
    
    return LegalActDetailResponse(
        id=act.id,
        nreg=act.nreg,
        title=act.title,
        is_processed=act.is_processed,
        processed_at=act.processed_at.isoformat() if act.processed_at else None,
        document_type=act.document_type,
        status=act.status,
        date_acceptance=act.date_acceptance.isoformat() if act.date_acceptance else None,
        date_publication=act.date_publication.isoformat() if act.date_publication else None,
        extracted_elements=act.extracted_elements,
        extracted_relations=act.extracted_relations,
        categories=categories
    )


@router.get("/{nreg:path}/check")
async def check_legal_act_exists(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    db: Session = Depends(get_db)
):
    """Check if legal act exists on Rada website"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    
    from app.services.rada_api import rada_api
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if already in database
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if act:
        return {
            "exists": True,
            "in_database": True,
            "is_processed": act.is_processed,
            "title": act.title,
            "message": "Акт знайдено в базі даних"
        }
    
    # Check on Rada website
    try:
        logger.info(f"Checking act {nreg} on Rada website...")
        document_json = await rada_api.get_document_json(nreg)
        if document_json:
            title = document_json.get("title", nreg)
            logger.info(f"Act {nreg} found on Rada website: {title}")
            return {
                "exists": True,
                "in_database": False,
                "is_processed": False,
                "title": title,
                "message": f"Акт знайдено на сайті data.rada.gov.ua: {title}"
            }
        else:
            logger.warning(f"Act {nreg} not found on Rada website")
            # Try alternative formats
            alternative_nregs = [
                nreg.replace('/', '-'),
                nreg.replace('к', 'к/'),
                nreg.upper(),
                nreg.lower()
            ]
            
            for alt_nreg in alternative_nregs:
                if alt_nreg == nreg:
                    continue
                logger.info(f"Trying alternative format: {alt_nreg}")
                alt_doc = await rada_api.get_document_json(alt_nreg)
                if alt_doc:
                    title = alt_doc.get("title", alt_nreg)
                    return {
                        "exists": True,
                        "in_database": False,
                        "is_processed": False,
                        "title": title,
                        "message": f"Акт знайдено на сайті data.rada.gov.ua (альтернативний формат): {title}"
                    }
            
            return {
                "exists": False,
                "in_database": False,
                "is_processed": False,
                "title": None,
                "message": f"Акт {nreg} не знайдено на сайті data.rada.gov.ua. Перевірте правильність номера реєстрації."
            }
    except Exception as e:
        logger.error(f"Error checking act {nreg}: {e}", exc_info=True)
        return {
            "exists": False,
            "in_database": False,
            "is_processed": False,
            "title": None,
            "message": f"Помилка при перевірці акту: {str(e)}"
        }


@router.post("/{nreg:path}/process")
async def process_legal_act(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Process a legal act (download, extract elements, sync to DBs)"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    
    # Check if OpenAI is configured
    from app.core.config import settings
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    from app.core.database import SessionLocal
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    async def process():
        # Create new session for background task
        bg_db = SessionLocal()
        try:
            logger.info(f"Starting background processing for {nreg}")
            bg_service = ProcessingService(bg_db)
            result = await bg_service.process_legal_act(nreg)
            if result:
                logger.info(f"Successfully processed {nreg}")
            else:
                logger.warning(f"Processing failed for {nreg}")
        except Exception as e:
            logger.error(f"Error processing {nreg}: {e}", exc_info=True)
        finally:
            bg_db.close()
    
    if background_tasks:
        background_tasks.add_task(lambda: asyncio.run(process()))
        return {"message": f"Processing started for {nreg}", "status": "queued"}
    else:
        # If no background tasks, process synchronously (for testing)
        import asyncio
        asyncio.run(process())
        return {"message": f"Processing completed for {nreg}", "status": "completed"}


# This route must be LAST to avoid matching /check, /details, /process as part of nreg
@router.get("/{nreg:path}", response_model=LegalActResponse)
async def get_legal_act(nreg: str = Path(..., description="Номер реєстрації акту"), db: Session = Depends(get_db)):
    """Get legal act by nreg"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if not act:
        raise HTTPException(status_code=404, detail=f"Legal act not found: {nreg}")
    return act
