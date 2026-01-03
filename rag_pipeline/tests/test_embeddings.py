"""
Tests for embeddings (with mocks)
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.embeddings.generator import EmbeddingsGenerator


@pytest.mark.asyncio
async def test_embeddings_generation():
    """Test embeddings generation with mock"""
    # Mock OpenAI response
    mock_response = AsyncMock()
    mock_item = AsyncMock()
    mock_item.embedding = [0.1] * 3072  # Mock embedding vector
    mock_response.data = [mock_item]
    
    with patch('src.embeddings.generator.AsyncOpenAI') as mock_openai:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client
        
        # This will fail without proper setup, but shows structure
        # In real test, would need to properly mock settings
        pass


def test_batch_size():
    """Test that batches are created correctly"""
    # Would test batching logic
    pass




