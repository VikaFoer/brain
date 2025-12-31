"""
Retrieval system for semantic search
"""
from typing import List, Dict, Any
import structlog
from src.embeddings.generator import EmbeddingsGenerator
from src.storage.dao import VectorDAO
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class Searcher:
    """Semantic search using embeddings"""
    
    def __init__(self):
        self.embeddings_gen = EmbeddingsGenerator()
        self.dao = VectorDAO()
    
    async def search(
        self,
        query: str,
        topk: int = None,
        similarity_threshold: float = None,
        doc_id: str = None,
        section_path: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks
        
        Args:
            query: Search query text
            topk: Number of results (default from config)
            similarity_threshold: Minimum similarity (default from config)
            doc_id: Filter by document ID
            section_path: Filter by section path
        
        Returns:
            List of similar chunks with metadata
        """
        topk = topk or settings.TOPK
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD
        
        # Generate query embedding
        logger.info("Generating query embedding", query=query[:100])
        query_chunks = [{"text": query}]
        embedded = await self.embeddings_gen.generate_embeddings(query_chunks)
        
        if not embedded or not embedded[0].get("embedding"):
            logger.error("Failed to generate query embedding")
            return []
        
        query_embedding = embedded[0]["embedding"]
        
        # Search in database
        logger.info("Searching database", topk=topk, threshold=similarity_threshold)
        results = self.dao.search_similar(
            query_embedding=query_embedding,
            topk=topk,
            similarity_threshold=similarity_threshold,
            doc_id=doc_id,
            section_path=section_path
        )
        
        logger.info("Search complete", results_count=len(results))
        return results

