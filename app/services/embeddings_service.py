"""
Service for generating embeddings for legal acts using OpenAI
"""
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings with chunking support"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            self.client = None
            logger.warning("OpenAI API key not configured. Embeddings will not be generated.")
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS
        
        # Token limits: ~8191 tokens ≈ 32764 characters (4 chars per token)
        # Use 30000 chars per chunk to be safe
        self.max_chunk_size = 30000  # characters per chunk
    
    def chunk_text(self, text: str, chunk_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks for embedding generation
        
        Args:
            text: Full text to chunk
            chunk_size: Maximum characters per chunk (default: self.max_chunk_size)
        
        Returns:
            List of chunks with metadata: [{"text": "...", "chunk_index": 0, "start": 0, "end": 30000}, ...]
        """
        if not text:
            return []
        
        chunk_size = chunk_size or self.max_chunk_size
        chunks = []
        
        # If text is shorter than chunk_size, return single chunk
        if len(text) <= chunk_size:
            return [{
                "text": text,
                "chunk_index": 0,
                "start": 0,
                "end": len(text),
                "total_chunks": 1
            }]
        
        # Split into chunks
        chunk_index = 0
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundary (for better context)
            if end < len(text):
                # Look for sentence endings within last 500 chars
                search_start = max(start, end - 500)
                for i in range(end - 1, search_start, -1):
                    if text[i] in ['.', '!', '?', '\n']:
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "start": start,
                    "end": end,
                    "total_chunks": None  # Will be set after all chunks are created
                })
                chunk_index += 1
            
            start = end
        
        # Set total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks
        
        logger.info(f"Split text into {total_chunks} chunks (max {chunk_size} chars each)")
        return chunks
    
    async def generate_embeddings(
        self,
        texts: List[str],
        use_batch: bool = True
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            use_batch: Whether to use batch API (cheaper: $0.065/1M tokens vs $0.13/1M)
        
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not self.client:
            logger.warning("OpenAI client not available. Cannot generate embeddings.")
            return [None] * len(texts)
        
        if not texts:
            return []
        
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "input": texts
            }
            
            # Add dimensions if specified (for text-embedding-3-large)
            if self.dimensions:
                api_params["dimensions"] = self.dimensions
            
            # Use batch API if requested and multiple texts
            if use_batch and len(texts) > 1:
                api_params["encoding_format"] = "float"  # Batch API requires explicit format
                logger.info(f"Generating embeddings for {len(texts)} texts using batch API...")
                response = await self.client.embeddings.create(**api_params)
            else:
                logger.info(f"Generating embeddings for {len(texts)} texts...")
                response = await self.client.embeddings.create(**api_params)
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [None] * len(texts)
    
    async def generate_embeddings_for_act(
        self,
        text: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for a legal act with chunking
        
        Args:
            text: Full text of the legal act
            title: Optional title to prepend to each chunk
        
        Returns:
            {
                "embeddings": [[float, ...], ...],  # List of embedding vectors
                "chunks": [{"text": "...", "chunk_index": 0, ...}, ...],  # Chunk metadata
                "model": "text-embedding-3-large",
                "dimensions": 3072
            }
        """
        if not text:
            return {
                "embeddings": [],
                "chunks": [],
                "model": self.model,
                "dimensions": self.dimensions
            }
        
        # Chunk the text
        chunks = self.chunk_text(text)
        
        if not chunks:
            return {
                "embeddings": [],
                "chunks": [],
                "model": self.model,
                "dimensions": self.dimensions
            }
        
        # Prepare texts for embedding (prepend title if provided)
        texts_to_embed = []
        for chunk in chunks:
            chunk_text = chunk["text"]
            if title:
                # Prepend title to maintain context
                chunk_text = f"{title}\n\n{chunk_text}"
            texts_to_embed.append(chunk_text)
        
        # Generate embeddings (use batch for cost efficiency)
        embeddings = await self.generate_embeddings(texts_to_embed, use_batch=True)
        
        # Combine results
        result = {
            "embeddings": embeddings,
            "chunks": chunks,
            "model": self.model,
            "dimensions": self.dimensions,
            "total_chunks": len(chunks)
        }
        
        logger.info(f"Generated {len(embeddings)} embeddings for act (model: {self.model}, dims: {self.dimensions})")
        return result
    
    async def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate a single embedding for short text (no chunking)
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector or None if error
        """
        if not text:
            return None
        
        embeddings = await self.generate_embeddings([text], use_batch=False)
        return embeddings[0] if embeddings else None


# Singleton instance
embeddings_service = EmbeddingsService()




