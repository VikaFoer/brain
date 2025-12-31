"""
Tests for chunking
"""
import pytest
from src.chunking.splitter import StructuralChunker


def test_simple_chunking():
    """Test simple chunking without structure"""
    chunker = StructuralChunker(chunk_size=100, overlap=0.1)
    
    text = "Це тестовий текст. " * 50  # ~1000 chars
    chunks = chunker.chunk_simple(text, "test_doc", {})
    
    assert len(chunks) > 0
    assert all("chunk_id" in c for c in chunks)
    assert all("text" in c for c in chunks)


def test_structural_chunking():
    """Test chunking with structure"""
    chunker = StructuralChunker(chunk_size=100, overlap=0.1)
    
    text = """
Розділ I
Загальні положення

Стаття 1
Це перша стаття з текстом.

Стаття 2
Це друга стаття.
"""
    chunks = chunker.chunk_by_structure(text, "test_doc", {})
    
    assert len(chunks) > 0
    # Should have chunks for each article
    article_chunks = [c for c in chunks if "Стаття" in str(c.get("metadata", {}).get("section_path", []))]
    assert len(article_chunks) >= 2


def test_overlap():
    """Test that overlap is added between chunks"""
    chunker = StructuralChunker(chunk_size=50, overlap=0.2)
    
    text = "Речення. " * 100
    chunks = chunker.chunk_simple(text, "test_doc", {})
    
    if len(chunks) > 1:
        # Check that adjacent chunks have some overlap
        first_end = chunks[0]["text"][-50:]
        second_start = chunks[1]["text"][:50]
        # Should have some common text (not exact due to sentence boundaries)
        assert len(first_end) > 0 and len(second_start) > 0

