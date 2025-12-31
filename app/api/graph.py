"""
API endpoints for graph operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.services.neo4j_service import neo4j_service
from pydantic import BaseModel

router = APIRouter()


class GraphNode(BaseModel):
    id: int
    label: str
    properties: dict


class GraphEdge(BaseModel):
    source: int
    target: int
    type: str
    properties: dict


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


@router.get("/categories", response_model=GraphResponse)
async def get_category_graph(
    category_ids: List[int] = Query(..., description="List of category IDs"),
    depth: int = Query(2, ge=1, le=5, description="Graph depth")
):
    """Get graph for selected categories"""
    if not category_ids:
        raise HTTPException(status_code=400, detail="At least one category ID required")
    
    graph_data = neo4j_service.get_category_graph(category_ids, depth)
    
    return GraphResponse(
        nodes=[GraphNode(**node) for node in graph_data["nodes"]],
        edges=[GraphEdge(**edge) for edge in graph_data["edges"]]
    )


@router.get("/relations")
async def get_relations_between_categories(
    category1_id: int = Query(..., description="First category ID"),
    category2_id: int = Query(..., description="Second category ID")
):
    """Get relations between two categories"""
    relations = neo4j_service.get_relations_between_categories(
        category1_id,
        category2_id
    )
    
    return {
        "category1_id": category1_id,
        "category2_id": category2_id,
        "relations": relations,
        "count": len(relations)
    }


@router.get("/statistics")
async def get_graph_statistics():
    """Get statistics for all categories in graph"""
    stats = neo4j_service.get_category_statistics()
    return {"statistics": stats}

