"""
OpenAI embeddings generator with batching and rate limiting
"""
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import structlog
from src.utils.config import settings
from src.utils.retry import retry_openai

logger = structlog.get_logger(__name__)


class EmbeddingsGenerator:
    """Generate embeddings using OpenAI API with batching"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBED_MODEL
        self.dimensions = settings.OPENAI_EMBED_DIMENSIONS
        self.batch_size = settings.BATCH_SIZE
        self.rate_limit_rpm = settings.RATE_LIMIT_RPM
        
        # Rate limiting
        self._last_request_time = 0
        self._min_interval = 60.0 / self.rate_limit_rpm
    
    async def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limit"""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_interval:
            wait_time = self._min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    @retry_openai
    async def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        await self._wait_for_rate_limit()
        
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        
        return [item.embedding for item in response.data]
    
    async def generate_embeddings(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks in batches
        
        Args:
            chunks: List of chunk dicts with "text" field
        
        Returns:
            List of chunks with "embedding" field added
        """
        total = len(chunks)
        logger.info("Starting embeddings generation", total_chunks=total, batch_size=self.batch_size)
        
        results = []
        
        for i in range(0, total, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            texts = [chunk["text"] for chunk in batch]
            
            try:
                embeddings = await self._generate_batch(texts)
                
                # Add embeddings to chunks
                for chunk, embedding in zip(batch, embeddings):
                    chunk["embedding"] = embedding
                    results.append(chunk)
                
                logger.info(
                    "Generated batch",
                    processed=i + len(batch),
                    total=total,
                    progress=f"{(i + len(batch)) / total * 100:.1f}%"
                )
                
            except Exception as e:
                logger.error("Failed to generate batch", batch_start=i, error=str(e))
                # Mark chunks as failed
                for chunk in batch:
                    chunk["embedding"] = None
                    chunk["error"] = str(e)
                    results.append(chunk)
        
        successful = sum(1 for r in results if r.get("embedding") is not None)
        logger.info("Embeddings generation complete", successful=successful, total=total)
        
        return results

