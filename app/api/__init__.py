from fastapi import APIRouter
from app.api import categories, legal_acts, graph, chat, status

router = APIRouter()

router.include_router(status.router, prefix="/status", tags=["status"])
router.include_router(categories.router, prefix="/categories", tags=["categories"])
router.include_router(legal_acts.router, prefix="/legal-acts", tags=["legal-acts"])
router.include_router(graph.router, prefix="/graph", tags=["graph"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])

