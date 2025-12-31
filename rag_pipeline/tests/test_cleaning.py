"""
Tests for text cleaning
"""
import pytest
from src.cleaning.cleaner import TextCleaner


def test_remove_page_numbers():
    """Test page number removal"""
    cleaner = TextCleaner()
    
    text = "Текст сторінки.\n\n5\n\nПродовження тексту."
    cleaned = cleaner.remove_page_numbers(text)
    
    assert "5" not in cleaned or "\n5\n" not in cleaned


def test_extract_reference_block():
    """Test reference block extraction"""
    cleaner = TextCleaner()
    
    text = """
Відомості про зміни до закону.
Це довідковий блок.

Розділ I
Основний текст документа.
"""
    main_text, ref_block = cleaner.extract_reference_block(text)
    
    assert "Відомості" in ref_block
    assert "Розділ I" in main_text
    assert "Відомості" not in main_text


def test_full_clean():
    """Test full cleaning pipeline"""
    cleaner = TextCleaner()
    
    text = """
    Верховна Рада України
    
    Текст документа.
    
    5
    
    Сторінка 1 з 10
    """
    
    result = cleaner.clean(text)
    
    assert "text" in result
    assert "metadata" in result
    assert len(result["text"]) > 0

