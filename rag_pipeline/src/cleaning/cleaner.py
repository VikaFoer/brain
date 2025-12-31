"""
Text cleaning utilities for legal documents
"""
import re
from typing import List, Tuple
import structlog

logger = structlog.get_logger(__name__)


class TextCleaner:
    """Clean legal document text"""
    
    # Patterns for common noise
    PAGE_NUMBER_PATTERNS = [
        r'\n\s*\d+\s*\n',  # Standalone page numbers
        r'^\s*\d+\s*$',  # Line with only page number
    ]
    
    FOOTER_PATTERNS = [
        r'Сторінка\s+\d+\s+з\s+\d+',
        r'Page\s+\d+\s+of\s+\d+',
        r'-\s*\d+\s*-',  # Page numbers like "- 5 -"
    ]
    
    HEADER_PATTERNS = [
        r'^.*?Верховна Рада.*?$',
        r'^.*?Кабінет Міністрів.*?$',
    ]
    
    # Patterns for reference blocks (довідковий блок)
    REFERENCE_BLOCK_PATTERNS = [
        r'^(?:Відомості|Інформація|Довідка).*?про.*?зміни.*?$',
        r'^.*?втратив.*?чинність.*?$',
        r'^.*?внесення.*?змін.*?$',
    ]
    
    @classmethod
    def remove_page_numbers(cls, text: str) -> str:
        """Remove page numbers"""
        for pattern in cls.PAGE_NUMBER_PATTERNS:
            text = re.sub(pattern, '\n', text, flags=re.MULTILINE)
        return text
    
    @classmethod
    def remove_footers(cls, text: str) -> str:
        """Remove footer patterns"""
        for pattern in cls.FOOTER_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
        return text
    
    @classmethod
    def remove_headers(cls, text: str) -> str:
        """Remove repeating headers"""
        lines = text.split('\n')
        cleaned_lines = []
        seen_headers = set()
        
        for line in lines:
            line_stripped = line.strip()
            is_header = False
            
            for pattern in cls.HEADER_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    if line_stripped.lower() in seen_headers:
                        is_header = True
                        break
                    seen_headers.add(line_stripped.lower())
                    break
            
            if not is_header:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def extract_reference_block(cls, text: str) -> Tuple[str, str]:
        """
        Extract reference block (довідковий блок) from text
        
        Returns:
            (cleaned_text, reference_block_text)
        """
        lines = text.split('\n')
        main_lines = []
        reference_lines = []
        in_reference = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if line starts reference block
            if not in_reference:
                for pattern in cls.REFERENCE_BLOCK_PATTERNS:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_reference = True
                        reference_lines.append(line)
                        break
                
                if not in_reference:
                    main_lines.append(line)
            else:
                # In reference block - collect until empty line or section break
                if line_stripped and not line_stripped.startswith(('Розділ', 'Стаття', 'Частина')):
                    reference_lines.append(line)
                else:
                    # End of reference block
                    in_reference = False
                    main_lines.append(line)
        
        return '\n'.join(main_lines), '\n'.join(reference_lines)
    
    @classmethod
    def remove_extra_whitespace(cls, text: str) -> str:
        """Remove excessive whitespace"""
        # Multiple newlines -> max 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Multiple spaces -> single space
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()
    
    @classmethod
    def clean(cls, text: str, extract_reference: bool = True) -> dict:
        """
        Clean text and return cleaned text + metadata
        
        Args:
            text: Raw text
            extract_reference: Whether to extract reference block
        
        Returns:
            {
                "text": cleaned_text,
                "reference_block": reference_block_text (if extracted),
                "metadata": {...}
            }
        """
        original_length = len(text)
        
        # Extract reference block first
        reference_block = ""
        if extract_reference:
            text, reference_block = cls.extract_reference_block(text)
        
        # Apply cleaning steps
        text = cls.remove_page_numbers(text)
        text = cls.remove_footers(text)
        text = cls.remove_headers(text)
        text = cls.remove_extra_whitespace(text)
        
        cleaned_length = len(text)
        reduction = original_length - cleaned_length
        
        return {
            "text": text,
            "reference_block": reference_block,
            "metadata": {
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "reduction_chars": reduction,
                "reduction_percent": (reduction / original_length * 100) if original_length > 0 else 0,
            }
        }

