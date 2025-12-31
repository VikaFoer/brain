"""
File extractors for PDF, HTML, DOCX, TXT
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import pypdf
from docx import Document
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)


class PDFExtractor:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract(file_path: Path) -> Dict[str, Any]:
        """Extract text and metadata from PDF"""
        try:
            with open(file_path, "rb") as f:
                pdf_reader = pypdf.PdfReader(f)
                
                # Check if PDF is scanned (no text content)
                text_content = ""
                total_chars = 0
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                        total_chars += len(page_text)
                
                # Determine if needs OCR
                needs_ocr = len(text_content.strip()) < 100  # Less than 100 chars = likely scan
                
                metadata = {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_type": "pdf",
                    "page_count": len(pdf_reader.pages),
                    "needs_ocr": needs_ocr,
                }
                
                # Extract PDF metadata if available
                if pdf_reader.metadata:
                    if pdf_reader.metadata.title:
                        metadata["title"] = pdf_reader.metadata.title
                    if pdf_reader.metadata.author:
                        metadata["author"] = pdf_reader.metadata.author
                
                return {
                    "text": text_content.strip(),
                    "metadata": metadata,
                }
        except Exception as e:
            logger.error("PDF extraction failed", file_path=str(file_path), error=str(e))
            raise


class HTMLExtractor:
    """Extract text from HTML files"""
    
    @staticmethod
    def extract(file_path: Path) -> Dict[str, Any]:
        """Extract text and metadata from HTML"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "lxml")
                
                # Remove script and style elements
                for script in soup(["script", "style", "meta", "link"]):
                    script.decompose()
                
                # Extract title
                title = None
                if soup.title:
                    title = soup.title.get_text().strip()
                elif soup.find("h1"):
                    title = soup.find("h1").get_text().strip()
                
                # Extract main content
                text = soup.get_text(separator="\n", strip=True)
                
                metadata = {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_type": "html",
                    "title": title,
                }
                
                return {
                    "text": text,
                    "metadata": metadata,
                }
        except Exception as e:
            logger.error("HTML extraction failed", file_path=str(file_path), error=str(e))
            raise


class DOCXExtractor:
    """Extract text from DOCX files"""
    
    @staticmethod
    def extract(file_path: Path) -> Dict[str, Any]:
        """Extract text and metadata from DOCX"""
        try:
            doc = Document(file_path)
            
            # Extract paragraphs
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            
            metadata = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": "docx",
            }
            
            # Extract core properties if available
            if doc.core_properties.title:
                metadata["title"] = doc.core_properties.title
            if doc.core_properties.author:
                metadata["author"] = doc.core_properties.author
            
            return {
                "text": text,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error("DOCX extraction failed", file_path=str(file_path), error=str(e))
            raise


class TXTExtractor:
    """Extract text from TXT files"""
    
    @staticmethod
    def extract(file_path: Path) -> Dict[str, Any]:
        """Extract text from TXT"""
        try:
            # Try different encodings
            encodings = ["utf-8", "utf-8-sig", "windows-1251", "cp866"]
            text = None
            
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                raise ValueError(f"Could not decode {file_path} with any encoding")
            
            metadata = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": "txt",
            }
            
            return {
                "text": text,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error("TXT extraction failed", file_path=str(file_path), error=str(e))
            raise


class FileExtractor:
    """Main extractor that routes to appropriate extractor"""
    
    EXTRACTORS = {
        ".pdf": PDFExtractor,
        ".html": HTMLExtractor,
        ".htm": HTMLExtractor,
        ".docx": DOCXExtractor,
        ".txt": TXTExtractor,
    }
    
    @classmethod
    def extract(cls, file_path: Path) -> Dict[str, Any]:
        """Extract text from file based on extension"""
        ext = file_path.suffix.lower()
        
        if ext not in cls.EXTRACTORS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        extractor_class = cls.EXTRACTORS[ext]
        result = extractor_class.extract(file_path)
        
        # Add file extension to metadata
        result["metadata"]["file_extension"] = ext
        
        return result

