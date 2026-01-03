"""
API endpoints for legal acts
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from urllib.parse import unquote
from app.core.database import get_db
from app.models.legal_act import LegalAct
from app.models.category import Category
from app.services.processing_service import ProcessingService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

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
    db: Session = Depends(get_db)
):
    """Get all legal acts"""
    try:
        # Ensure tables exist
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        # Try to add new columns if they don't exist (for existing databases)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('legal_acts')]
            
            # Add dataset_id if missing
            if 'dataset_id' not in columns:
                logger.warning("Column 'dataset_id' not found in legal_acts table, adding it...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN dataset_id VARCHAR(100)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_legal_acts_dataset_id ON legal_acts(dataset_id)"))
                    conn.commit()
                logger.info("Column 'dataset_id' added successfully")
            
            # Add dataset_metadata if missing
            if 'dataset_metadata' not in columns:
                logger.warning("Column 'dataset_metadata' not found in legal_acts table, adding it...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN dataset_metadata JSON"))
                    conn.commit()
                logger.info("Column 'dataset_metadata' added successfully")
            
            # Add source if missing
            if 'source' not in columns:
                logger.warning("Column 'source' not found in legal_acts table, adding it...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN source VARCHAR(50) DEFAULT 'rada_api'"))
                    conn.commit()
                logger.info("Column 'source' added successfully")
        except Exception as migration_error:
            # Column might already exist or migration failed, continue
            logger.debug(f"Migration check: {migration_error}")
        
        # Get acts from database
        # First ensure migration is complete by checking if new columns exist
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('legal_acts')]
            
            # If new columns don't exist, use explicit column selection to avoid errors
            if 'dataset_id' not in columns or 'dataset_metadata' not in columns or 'source' not in columns:
                # Use explicit column selection without new fields
                from sqlalchemy import select, column
                acts = db.execute(
                    select(
                        LegalAct.id,
                        LegalAct.nreg,
                        LegalAct.title,
                        LegalAct.is_processed,
                        LegalAct.document_type,
                        LegalAct.status,
                        LegalAct.date_acceptance,
                        LegalAct.date_publication
                    ).order_by(LegalAct.created_at.desc()).limit(100)
                ).all()
                # Convert to LegalAct-like objects
                result = []
                for row in acts:
                    result.append(LegalActResponse(
                        id=row.id,
                        nreg=row.nreg,
                        title=row.title,
                        is_processed=row.is_processed,
                        document_type=row.document_type,
                        status=row.status,
                        date_acceptance=row.date_acceptance.isoformat() if row.date_acceptance else None,
                        date_publication=row.date_publication.isoformat() if row.date_publication else None
                    ))
                return result
        except Exception as migration_check_error:
            logger.debug(f"Migration check failed: {migration_check_error}, using standard query")
        
        # Standard query if migration is complete
        acts = db.query(LegalAct).order_by(LegalAct.created_at.desc()).limit(100).all()
        
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
    except Exception as e:
        logger.error(f"Error getting legal acts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )




@router.get("/test-open-data-api")
async def test_open_data_api(db: Session = Depends(get_db)):
    """
    Test open data portal API - find and fetch legal acts dataset
    """
    from app.services.rada_api import rada_api
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Try to find dataset ID
        logger.info("Searching for legal acts dataset ID...")
        dataset_id = await rada_api.find_legal_acts_dataset_id()
        
        if not dataset_id:
            return {
                "status": "error",
                "message": "Could not find legal acts dataset ID",
                "suggestion": "Try visiting https://data.rada.gov.ua/ogd/ and find the dataset ID manually"
            }
        
        # Try to fetch dataset
        logger.info(f"Found dataset ID: {dataset_id}, fetching data...")
        nregs = await rada_api.get_all_nregs_from_open_data(dataset_id=dataset_id)
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "nregs_count": len(nregs),
            "sample_nregs": nregs[:10] if nregs else [],
            "message": f"Successfully fetched {len(nregs)} NREG identifiers from open data portal"
        }
    except Exception as e:
        logger.error(f"Error testing open data API: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }




@router.post("/initialize-categories")
@router.get("/initialize-categories")  # Also allow GET for browser access
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
            "message": f"Categories initialized successfully. Total categories: {count}",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error initializing categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing categories: {str(e)}"
        )


@router.post("/import-categories")
async def import_categories(
    categories: List[Dict[str, Any]] = Body(..., description="List of categories with format: [{'code': int, 'name': str}]"),
    db: Session = Depends(get_db)
):
    """
    Import categories from list
    """
    from app.models.category import Category
    from app.services.neo4j_service import neo4j_service
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        created = 0
        updated = 0
        
        for cat_data in categories:
            code = cat_data.get("code")
            name = cat_data.get("name")
            
            if not name:
                continue
            
            # Check if category exists by name
            existing = db.query(Category).filter(Category.name == name).first()
            
            if existing:
                # Update existing category
                if code is not None:
                    existing.code = code
                updated += 1
            else:
                # Create new category
                new_category = Category(name=name, code=code)
                db.add(new_category)
                created += 1
                
                # Also create in Neo4j
                try:
                    neo4j_service.create_category_node(
                        category_id=new_category.id,
                        name=new_category.name,
                        element_count=0,
                        code=new_category.code
                    )
                except Exception as e:
                    logger.warning(f"Failed to create category in Neo4j: {e}")
        
        db.commit()
        
        return {
            "message": f"Categories imported successfully. Created: {created}, Updated: {updated}",
            "created": created,
            "updated": updated
        }
    except Exception as e:
        logger.error(f"Error importing categories: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error importing categories: {str(e)}"
        )


@router.get("/{nreg:path}/check")
async def check_legal_act_exists(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    db: Session = Depends(get_db)
):
    """
    Check if legal act exists on Rada website and in database
    """
    from app.services.rada_api import rada_api
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    
    try:
        # Check in database first
        act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
        
        if act:
            return {
                "exists": True,
                "in_database": True,
                "is_processed": act.is_processed,
                "title": act.title,
                "message": f"Act {nreg} exists in database"
            }
        
        # Check on Rada website
        try:
            card_json = await rada_api.get_document_card(nreg)
            
            if card_json:
                # Try to get alternative NREG formats
                alternative_nregs = []
                if card_json.get("nreg"):
                    alternative_nregs.append(card_json.get("nreg"))
                if card_json.get("number"):
                    alternative_nregs.append(card_json.get("number"))
                if card_json.get("id"):
                    alternative_nregs.append(card_json.get("id"))
                
                # Check if any alternative exists in DB
                for alt_nreg in alternative_nregs:
                    if alt_nreg:
                        alt_act = db.query(LegalAct).filter(LegalAct.nreg == alt_nreg).first()
                        if alt_act:
                            return {
                                "exists": True,
                                "in_database": True,
                                "is_processed": alt_act.is_processed,
                                "title": alt_act.title,
                                "message": f"Act found with alternative NREG: {alt_nreg}"
                            }
                
                return {
                    "exists": True,
                    "in_database": False,
                    "is_processed": False,
                    "title": card_json.get("title", nreg),
                    "message": f"Act {nreg} exists on Rada website but not in database"
                }
        except Exception as e:
            logger.debug(f"Error checking act on Rada: {e}")
        
        return {
            "exists": False,
            "in_database": False,
            "is_processed": False,
            "title": None,
            "message": f"Act {nreg} not found"
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


@router.get("/rada-list")
async def get_rada_acts_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Отримати список всіх НПА з бази даних
    Повертає список документів з інформацією про те, які вже завантажені та оброблені
    Більше не витягує NREG з API - використовує тільки дані з БД
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Ensure migration is complete before querying
        from app.core.database import Base, engine
        Base.metadata.create_all(bind=engine)
        
        # Try to add new columns if they don't exist
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('legal_acts')]
            
            if 'dataset_id' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN IF NOT EXISTS dataset_id VARCHAR(100)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_legal_acts_dataset_id ON legal_acts(dataset_id)"))
                    conn.commit()
            
            if 'dataset_metadata' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN IF NOT EXISTS dataset_metadata JSON"))
                    conn.commit()
            
            if 'source' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE legal_acts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'rada_api'"))
                    conn.commit()
        except Exception as migration_error:
            logger.debug(f"Migration check: {migration_error}")
        
        # Get all acts from database (no API calls for NREG extraction)
        all_acts = db.query(LegalAct).order_by(LegalAct.created_at.desc()).all()
        
        if not all_acts:
            return {
                "total": 0,
                "loaded": 0,
                "processed": 0,
                "not_loaded": 0,
                "skip": skip,
                "limit": limit,
                "has_more": False,
                "acts": [],
                "message": "Список НПА порожній. Натисніть 'Завантажити з датасету' або 'Завантажити всі НПА' для отримання переліку."
            }
        
        # Build response with status for each act
        acts_list = []
        for act in all_acts:
            acts_list.append({
                "nreg": act.nreg,
                "title": act.title if act.title else act.nreg,
                "in_database": True,  # All acts in DB are loaded
                "is_processed": act.is_processed if act.is_processed else False,
                "status": "processed" if act.is_processed else "loaded",
                "status_label": "✅ Оброблено" if act.is_processed else "📥 Завантажено",
                "source": getattr(act, 'source', 'rada_api'),
                "dataset_id": getattr(act, 'dataset_id', None)
            })
        
        loaded_count = len(acts_list)
        processed_count = len([a for a in acts_list if a["is_processed"]])
        
        # Apply pagination
        total_count = len(acts_list)
        paginated_acts = acts_list[skip:skip + limit]
        
        return {
            "total": total_count,
            "loaded": loaded_count,
            "processed": processed_count,
            "not_loaded": 0,  # All are in DB
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total_count,
            "acts": paginated_acts
        }
        
    except Exception as e:
        logger.error(f"Error getting Rada acts list: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Rada acts list: {str(e)}"
        )


@router.post("/download-from-dataset")
async def download_all_from_dataset(
    background_tasks: BackgroundTasks,
    dataset_id: Optional[str] = Query(None, description="Dataset ID (e.g., 'docs', 'laws'). If not provided, will auto-detect"),
    limit: Optional[int] = Query(None, description="Limit number of documents to download"),
    db: Session = Depends(get_db)
):
    """
    Завантажити ВСІ документи з open data датасету без фільтрації по NREG
    Створює записи в БД з усією доступною інформацією з датасету
    """
    from app.services.rada_api import rada_api
    from app.core.database import SessionLocal
    import asyncio
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    async def download_all_documents_task():
        """Background task для завантаження всіх документів з датасету"""
        bg_db = SessionLocal()
        try:
            logger.info(f"Starting download of ALL documents from open data dataset (dataset_id={dataset_id})...")
            
            # Get all documents from dataset
            all_documents = await rada_api.get_all_documents_from_dataset(dataset_id=dataset_id, limit=limit)
            
            if not all_documents:
                logger.error("No documents found in dataset")
                return
            
            logger.info(f"Found {len(all_documents)} documents in dataset")
            
            # Get existing NREGs from database
            existing_nregs = {act.nreg for act in bg_db.query(LegalAct.nreg).all()}
            
            # Create or update acts in database
            created = 0
            updated = 0
            skipped = 0
            
            for doc in all_documents:
                try:
                    # Extract NREG from document
                    nreg = (doc.get("nreg") or doc.get("NREG") or 
                           doc.get("id") or doc.get("number") or 
                           doc.get("identifier") or f"doc_{created}")
                    
                    # Extract title
                    title = (doc.get("title") or doc.get("name") or 
                            doc.get("Title") or doc.get("Name") or nreg)
                    
                    # Extract status
                    status = (doc.get("status") or doc.get("Status") or 
                             doc.get("статус") or doc.get("Статус"))
                    
                    # Extract dates
                    date_acceptance = None
                    date_publication = None
                    
                    for date_field in ["date_acceptance", "date_publication", "date", "Date", 
                                      "дата_прийняття", "дата_опублікування"]:
                        if date_field in doc and doc[date_field]:
                            try:
                                from dateutil import parser
                                parsed_date = parser.parse(str(doc[date_field]))
                                if "acceptance" in date_field.lower() or "прийняття" in date_field.lower():
                                    date_acceptance = parsed_date
                                elif "publication" in date_field.lower() or "опублікування" in date_field.lower():
                                    date_publication = parsed_date
                                elif not date_acceptance:
                                    date_acceptance = parsed_date
                            except:
                                pass
                    
                    # Extract document type
                    document_type = (doc.get("document_type") or doc.get("type") or 
                                    doc.get("DocumentType") or doc.get("Type"))
                    
                    # Check if already exists
                    act = bg_db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
                    
                    if act:
                        # Update with dataset information
                        if not act.title or act.title == act.nreg:
                            act.title = title
                        if status and not act.status:
                            act.status = status
                        if document_type and not act.document_type:
                            act.document_type = document_type
                        if date_acceptance and not act.date_acceptance:
                            act.date_acceptance = date_acceptance
                        if date_publication and not act.date_publication:
                            act.date_publication = date_publication
                        
                        # Update dataset metadata
                        act.dataset_id = dataset_id or doc.get("_dataset_id")
                        act.dataset_metadata = doc
                        act.source = "open_data"
                        
                        updated += 1
                    else:
                        # Create new act with all available information
                        new_act = LegalAct(
                            nreg=nreg,
                            title=title,
                            status=status,
                            document_type=document_type,
                            date_acceptance=date_acceptance,
                            date_publication=date_publication,
                            dataset_id=dataset_id or doc.get("_dataset_id"),
                            dataset_metadata=doc,
                            source="open_data",
                            is_processed=False
                        )
                        bg_db.add(new_act)
                        created += 1
                    
                    # Commit every 100 acts
                    if (created + updated) % 100 == 0:
                        bg_db.commit()
                        logger.info(f"Progress: {created} created, {updated} updated, {skipped} skipped (total processed: {created + updated})")
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('nreg', 'unknown')}: {e}")
                    bg_db.rollback()
                    skipped += 1
                    continue
            
            # Final commit
            bg_db.commit()
            logger.info(f"Download completed: {created} created, {updated} updated, {skipped} skipped, total: {len(all_documents)}")
            
        except Exception as e:
            logger.error(f"Error in download_all_documents_task: {e}", exc_info=True)
        finally:
            bg_db.close()
    
    background_tasks.add_task(lambda: asyncio.run(download_all_documents_task()))
    return {
        "message": f"Завантаження документів з датасету запущено в фоновому режимі (dataset_id={dataset_id})",
        "status": "queued",
        "dataset_id": dataset_id
    }


@router.post("/rada-list/sync-all")
async def sync_all_rada_acts(
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Одноразове завантаження ВСІХ НПА з open data датасету в базу даних
    Використовує новий метод get_all_documents_from_dataset (без витягування NREG)
    """
    from app.services.rada_api import rada_api
    from app.core.database import SessionLocal
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    async def sync_all_acts():
        """Background task для завантаження всіх НПА"""
        bg_db = SessionLocal()
        try:
            logger.info("Starting sync of ALL legal acts from open data dataset...")
            
            # Get all documents from dataset (without NREG filtering)
            all_documents = await rada_api.get_all_documents_from_dataset(limit=None)
            
            if not all_documents:
                logger.error("No documents found in dataset")
                return
            
            logger.info(f"Found {len(all_documents)} total documents in dataset")
            
            # Get existing NREGs from database
            existing_nregs = {act.nreg for act in bg_db.query(LegalAct.nreg).all()}
            
            # Create or update acts in database
            created = 0
            updated = 0
            skipped = 0
            
            for doc in all_documents:
                # Extract NREG from document
                nreg = (doc.get("nreg") or doc.get("NREG") or 
                       doc.get("id") or doc.get("number") or 
                       doc.get("identifier") or f"doc_{created}")
                
                # Extract title
                title = (doc.get("title") or doc.get("name") or 
                        doc.get("Title") or doc.get("Name") or nreg)
                try:
                    # Check if already exists
                    act = bg_db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
                    
                    if act:
                        # Update if needed (e.g., if title is missing or metadata is missing)
                        if not act.title or act.title == act.nreg:
                            act.title = title
                        if not act.dataset_metadata:
                            act.dataset_metadata = doc
                            act.dataset_id = doc.get("_dataset_id")
                            act.source = "open_data"
                        updated += 1
                    else:
                        # Create new act with all available information
                        new_act = LegalAct(
                            nreg=nreg,
                            title=title,
                            dataset_metadata=doc,
                            dataset_id=doc.get("_dataset_id"),
                            source="open_data",
                            is_processed=False
                        )
                        bg_db.add(new_act)
                        created += 1
                    
                    # Commit every 100 acts
                    if (created + updated) % 100 == 0:
                        bg_db.commit()
                        logger.info(f"Progress: {created} created, {updated} updated, {skipped} skipped (total processed: {created + updated})")
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('nreg', 'unknown')}: {e}")
                    bg_db.rollback()
                    skipped += 1
                    continue
            
            # Final commit
            bg_db.commit()
            logger.info(f"Sync completed: {created} created, {updated} updated, {skipped} skipped, total: {len(all_documents)}")
            
        except Exception as e:
            logger.error(f"Error in sync_all_acts: {e}", exc_info=True)
        finally:
            bg_db.close()
    
    background_tasks.add_task(lambda: asyncio.run(sync_all_acts()))
    return {
        "message": "Завантаження всіх НПА з датасету запущено в фоновому режимі.",
        "status": "queued"
    }


@router.post("/download-active-acts")
async def download_active_acts(
    background_tasks: BackgroundTasks,
    process: bool = Query(False, description="Обробити через OpenAI після завантаження"),
    db: Session = Depends(get_db)
):
    """
    Завантажити всі ДІЮЧІ нормативно-правові акти з open data датасету
    Фільтрує тільки акти зі статусом "діє", "чинний" тощо
    Використовує новий метод get_all_documents_from_dataset (без витягування NREG)
    """
    from app.services.rada_api import rada_api
    from app.core.database import SessionLocal
    from app.services.processing_service import ProcessingService
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Статуси, які вважаються "діючими"
    ACTIVE_STATUSES = ["діє", "діючий", "в дії", "чинний", "active", "valid", "в силі"]
    
    def is_active_status(status):
        """Перевірити, чи статус вказує на діючий акт"""
        if status is None:
            return True
        
        status_lower = str(status).lower().strip()
        
        for active_status in ACTIVE_STATUSES:
            if active_status.lower() in status_lower:
                return True
        
        inactive_keywords = ["втратив", "скасовано", "недійсний", "застарілий", "втратив чинність"]
        for keyword in inactive_keywords:
            if keyword in status_lower:
                return False
        
        return True
    
    async def download_and_process_active():
        """Background task для завантаження та обробки діючих НПА"""
        bg_db = SessionLocal()
        try:
            logger.info("🚀 Початок завантаження ДІЮЧИХ нормативно-правових актів...")
            
            # Отримати всі документи з датасету (без фільтрації по NREG)
            all_documents = []
            try:
                logger.info("Спроба отримати документи через open data portal API...")
                all_documents = await rada_api.get_all_documents_from_dataset()
                if all_documents:
                    logger.info(f"✅ Отримано {len(all_documents)} документів через open data portal")
            except Exception as e:
                logger.warning(f"Open data API не працює: {e}")
            
            if not all_documents:
                logger.error("❌ Не вдалося отримати документи з датасету")
                return
            
            logger.info(f"📋 Знайдено {len(all_documents)} загальних документів")
            
            # Фільтрувати діючі
            active_documents = []
            existing_nregs = {act.nreg for act in bg_db.query(LegalAct.nreg).all()}
            created = 0
            updated = 0
            skipped_inactive = 0
            
            logger.info("🔍 Фільтрація діючих актів...")
            
            for doc in all_documents:
                try:
                    # Extract NREG from document
                    nreg = (doc.get("nreg") or doc.get("NREG") or 
                           doc.get("id") or doc.get("number") or 
                           doc.get("identifier") or f"doc_{created}")
                    
                    # Extract status from document metadata
                    status = (doc.get("status") or doc.get("Status") or 
                             doc.get("статус") or doc.get("Статус"))
                    
                    # Check if status is active
                    if not is_active_status(status):
                        skipped_inactive += 1
                        continue
                    
                    # Extract title
                    title = (doc.get("title") or doc.get("name") or 
                            doc.get("Title") or doc.get("Name") or nreg)
                    
                    # Створити або оновити акт
                    existing_act = bg_db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
                    
                    if existing_act:
                        if not existing_act.title or existing_act.title == nreg:
                            existing_act.title = title
                            existing_act.status = status
                        if not existing_act.dataset_metadata:
                            existing_act.dataset_metadata = doc
                            existing_act.dataset_id = doc.get("_dataset_id")
                            existing_act.source = "open_data"
                        updated += 1
                    else:
                        new_act = LegalAct(
                            nreg=nreg,
                            title=title,
                            status=status,
                            dataset_metadata=doc,
                            dataset_id=doc.get("_dataset_id"),
                            source="open_data",
                            is_processed=False
                        )
                        bg_db.add(new_act)
                        active_documents.append(nreg)
                        created += 1
                    
                    # Коміт батчами
                    if (created + updated) % 100 == 0:
                        bg_db.commit()
                        logger.info(f"Прогрес: {created} створено, {updated} оновлено, {skipped_inactive} пропущено (недіючі)")
                
                except Exception as e:
                    logger.error(f"Помилка обробки документа {doc.get('nreg', 'unknown')}: {e}")
                    bg_db.rollback()
                    continue
            
            bg_db.commit()
            logger.info(f"✅ Завантаження завершено: {created} створено, {updated} оновлено, {skipped_inactive} пропущено (недіючі)")
            
            # Обробка через OpenAI якщо потрібно
            if process and active_documents:
                logger.info(f"🤖 Початок обробки {len(active_documents)} діючих НПА через OpenAI...")
                processing_service = ProcessingService(bg_db)
                processed = 0
                failed = 0
                
                for nreg in active_documents:
                    try:
                        result = await processing_service.process_legal_act(nreg)
                        if result and result.is_processed:
                            processed += 1
                        else:
                            failed += 1
                        
                        if (processed + failed) % 50 == 0:
                            bg_db.commit()
                            logger.info(f"Обробка: {processed} оброблено, {failed} помилок")
                    except Exception as e:
                        logger.error(f"Помилка обробки {nreg}: {e}")
                        failed += 1
                
                bg_db.commit()
                logger.info(f"✅ Обробка завершена: {processed} оброблено, {failed} помилок")
            
        except Exception as e:
            logger.error(f"Error in download_and_process_active: {e}", exc_info=True)
        finally:
            bg_db.close()
    
    background_tasks.add_task(lambda: asyncio.run(download_and_process_active()))
    return {
        "message": "Завантаження діючих НПА запущено в фоновому режимі.",
        "status": "queued",
        "process_requested": process
    }


@router.post("/process")
async def process_legal_act(
    nreg: str = Body(..., description="Номер реєстрації акту"),
    force_reprocess: bool = Query(False, description="Переобробити навіть якщо вже оброблено"),
    db: Session = Depends(get_db)
):
    """
    Process a legal act: download, extract elements, sync to both DBs
    """
    processing_service = ProcessingService(db)
    
    try:
        result = await processing_service.process_legal_act(nreg, force_reprocess=force_reprocess)
        
        if result:
            return {
                "message": f"Act {nreg} processed successfully",
                "nreg": result.nreg,
                "title": result.title,
                "is_processed": result.is_processed,
                "processed_at": result.processed_at.isoformat() if result.processed_at else None
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Could not process act {nreg}. Act may not exist or could not be downloaded."
            )
    except Exception as e:
        logger.error(f"Error processing act {nreg}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing act: {str(e)}"
        )


@router.get("/{nreg:path}", response_model=LegalActResponse)
async def get_legal_act(
    nreg: str = Path(..., description="Номер реєстрації акту"),
    db: Session = Depends(get_db)
):
    """Get legal act by NREG"""
    # Decode URL-encoded characters
    nreg = unquote(nreg)
    act = db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
    if not act:
        raise HTTPException(status_code=404, detail="Legal act not found")
    
    return LegalActResponse(
        id=act.id,
        nreg=act.nreg,
        title=act.title,
        is_processed=act.is_processed,
        document_type=act.document_type,
        status=act.status,
        date_acceptance=act.date_acceptance.isoformat() if act.date_acceptance else None,
        date_publication=act.date_publication.isoformat() if act.date_publication else None
    )
