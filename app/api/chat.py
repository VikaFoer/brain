"""
API endpoints for chat with OpenAI
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.models.category import Category
from app.models.legal_act import LegalAct, ActCategory
from app.services.openai_service import openai_service
from app.services.neo4j_service import neo4j_service
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    category_ids: Optional[List[int]] = None
    context_type: Optional[str] = "general"  # relations, elements, general
    conversation_history: Optional[List[Dict[str, str]]] = None  # For context


class ChatResponse(BaseModel):
    answer: str
    context_used: dict
    relevant_acts: List[dict] = []
    relevant_categories: List[dict] = []


def search_relevant_acts(question: str, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for relevant legal acts based on question"""
    try:
        # Split question into keywords for better search
        keywords = question.lower().split()
        keywords = [kw for kw in keywords if len(kw) > 2]  # Filter short words
        
        # Search in title and text
        acts = db.query(LegalAct).filter(
            or_(
                *[LegalAct.title.ilike(f"%{kw}%") for kw in keywords],
                *[LegalAct.text.ilike(f"%{kw}%") for kw in keywords],
                LegalAct.nreg.ilike(f"%{question}%")
            )
        ).limit(limit * 2).all()  # Get more to filter by relevance
        
        # Also search in extracted elements for processed acts
        processed_acts = db.query(LegalAct).filter(
            LegalAct.is_processed == True,
            LegalAct.extracted_elements.isnot(None)
        ).limit(limit * 2).all()
        
        # Check if extracted elements contain keywords
        relevant_processed = []
        for act in processed_acts:
            if act.extracted_elements:
                elements_str = str(act.extracted_elements).lower()
                if any(kw in elements_str for kw in keywords):
                    relevant_processed.append(act)
        
        # Combine and deduplicate
        all_acts = list(acts) + relevant_processed
        seen_nregs = set()
        unique_acts = []
        for act in all_acts:
            if act.nreg not in seen_nregs:
                seen_nregs.add(act.nreg)
                unique_acts.append(act)
            if len(unique_acts) >= limit:
                break
        
        result = []
        for act in unique_acts:
            act_data = {
                "nreg": act.nreg,
                "title": act.title,
                "document_type": act.document_type,
                "status": act.status,
                "is_processed": act.is_processed,
                "date_acceptance": act.date_acceptance.isoformat() if act.date_acceptance else None,
                "date_publication": act.date_publication.isoformat() if act.date_publication else None,
            }
            
            # Include extracted elements if available
            if act.is_processed and act.extracted_elements:
                act_data["extracted_elements"] = act.extracted_elements
                # Limit elements to avoid too much data
                if isinstance(act.extracted_elements, dict):
                    elements = act.extracted_elements.get("elements", [])
                    if isinstance(elements, list) and len(elements) > 5:
                        act_data["extracted_elements"] = {
                            **act.extracted_elements,
                            "elements": elements[:5]  # First 5 elements
                        }
            
            result.append(act_data)
        return result
    except Exception as e:
        logger.error(f"Error searching acts: {e}")
        return []


def search_relevant_categories(question: str, db: Session) -> List[Dict[str, Any]]:
    """Search for relevant categories based on question"""
    try:
        categories = db.query(Category).filter(
            Category.name.ilike(f"%{question}%")
        ).limit(5).all()
        
        result = []
        for cat in categories:
            # Get acts count for this category
            acts_count = db.query(func.count(ActCategory.act_id)).filter(
                ActCategory.category_id == cat.id
            ).scalar() or 0
            
            result.append({
                "id": cat.id,
                "name": cat.name,
                "element_count": cat.element_count,
                "acts_count": acts_count
            })
        return result
    except Exception as e:
        logger.error(f"Error searching categories: {e}")
        return []


def get_database_statistics(db: Session) -> Dict[str, Any]:
    """Get general database statistics"""
    try:
        total_acts = db.query(func.count(LegalAct.id)).scalar() or 0
        processed_acts = db.query(func.count(LegalAct.id)).filter(
            LegalAct.is_processed == True
        ).scalar() or 0
        total_categories = db.query(func.count(Category.id)).scalar() or 0
        
        return {
            "total_acts": total_acts,
            "processed_acts": processed_acts,
            "total_categories": total_categories,
            "processing_rate": round((processed_acts / total_acts * 100) if total_acts > 0 else 0, 2)
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {}


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Chat about legal acts, categories, and relations using database data"""
    
    # Build context from database
    context = {
        "database_statistics": get_database_statistics(db)
    }
    
    # Search for relevant acts and categories based on question
    relevant_acts = search_relevant_acts(request.question, db, limit=5)
    relevant_categories = search_relevant_categories(request.question, db)
    
    context["relevant_acts"] = relevant_acts
    context["relevant_categories"] = relevant_categories
    
    # If specific categories requested, get their info
    if request.category_ids:
        categories = db.query(Category).filter(
            Category.id.in_(request.category_ids)
        ).all()
        
        context["selected_categories"] = [
            {
                "id": cat.id,
                "name": cat.name,
                "element_count": cat.element_count
            }
            for cat in categories
        ]
        
        # Get acts for selected categories
        acts_in_categories = db.query(LegalAct).join(
            ActCategory
        ).filter(
            ActCategory.category_id.in_(request.category_ids)
        ).limit(10).all()
        
        context["acts_in_categories"] = [
            {
                "nreg": act.nreg,
                "title": act.title,
                "is_processed": act.is_processed
            }
            for act in acts_in_categories
        ]
        
        # Get relations between categories if multiple selected
        if len(request.category_ids) >= 2:
            try:
                relations = neo4j_service.get_relations_between_categories(
                    request.category_ids[0],
                    request.category_ids[1]
                )
                context["relations"] = relations[:10] if relations else []
            except:
                context["relations"] = []
        
        # Get statistics
        try:
            stats = neo4j_service.get_category_statistics()
            context["statistics"] = [
                s for s in stats if s.get("id") in request.category_ids
            ] if stats else []
        except:
            context["statistics"] = []
    
    # Always include extracted elements from relevant acts if available
    # This helps answer questions about content of legal acts
    for act_data in relevant_acts:
        if act_data.get("is_processed") and act_data.get("extracted_elements"):
            # Elements already included in search_relevant_acts result
            pass
    
    # Get additional processed acts with extracted elements for general questions
    # This ensures we have context even if search didn't find exact matches
    if len(relevant_acts) == 0 or any("функці" in request.question.lower() or "держав" in request.question.lower() or "конституці" in request.question.lower() for _ in [1]):
        processed_acts = db.query(LegalAct).filter(
            LegalAct.is_processed == True,
            LegalAct.extracted_elements.isnot(None)
        ).limit(10).all()
        
        context["processed_acts_with_elements"] = []
        for act in processed_acts:
            act_info = {
                "nreg": act.nreg,
                "title": act.title,
                "has_elements": bool(act.extracted_elements),
                "has_relations": bool(act.extracted_relations)
            }
            # Include extracted elements for better context
            if act.extracted_elements:
                if isinstance(act.extracted_elements, dict):
                    elements = act.extracted_elements.get("elements", [])
                    if isinstance(elements, list) and len(elements) > 0:
                        # Include all elements, not just sample
                        act_info["extracted_elements"] = act.extracted_elements
                else:
                    act_info["extracted_elements"] = act.extracted_elements
            context["processed_acts_with_elements"].append(act_info)
    
    # Get answer from OpenAI with full context
    answer = await openai_service.chat_about_database(
        request.question,
        context,
        conversation_history=request.conversation_history or []
    )
    
    return ChatResponse(
        answer=answer,
        context_used=context,
        relevant_acts=relevant_acts,
        relevant_categories=relevant_categories
    )

