"""
API endpoints for chat with OpenAI
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.category import Category
from app.models.legal_act import LegalAct
from app.services.openai_service import openai_service
from app.services.neo4j_service import neo4j_service
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    category_ids: Optional[List[int]] = None
    context_type: Optional[str] = "relations"  # relations, elements, general


class ChatResponse(BaseModel):
    answer: str
    context_used: dict


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Chat about relations and legal acts"""
    
    # Build context
    context = {}
    
    if request.category_ids:
        # Get categories info
        categories = db.query(Category).filter(
            Category.id.in_(request.category_ids)
        ).all()
        
        context["categories"] = [
            {
                "id": cat.id,
                "name": cat.name,
                "element_count": cat.element_count
            }
            for cat in categories
        ]
        
        # Get relations between categories if multiple selected
        if len(request.category_ids) >= 2:
            relations = neo4j_service.get_relations_between_categories(
                request.category_ids[0],
                request.category_ids[1]
            )
            context["relations"] = relations[:10]  # Limit to 10
        
        # Get statistics
        stats = neo4j_service.get_category_statistics()
        context["statistics"] = [
            s for s in stats if s["id"] in request.category_ids
        ]
    
    # Get answer from OpenAI
    answer = await openai_service.chat_about_relations(
        request.question,
        context
    )
    
    return ChatResponse(
        answer=answer,
        context_used=context
    )

