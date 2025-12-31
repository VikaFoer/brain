"""
Structural chunker for legal documents
"""
import re
from typing import List, Dict, Any, Optional
import tiktoken
import structlog
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class StructuralChunker:
    """Chunk legal documents by structure (Розділ → Стаття → Частина → Пункт)"""
    
    # Patterns for document structure
    SECTION_PATTERN = r'^(?:Розділ|РОЗДІЛ)\s+([IVX\d]+)'
    ARTICLE_PATTERN = r'^Стаття\s+(\d+)'
    PART_PATTERN = r'^Частина\s+(\d+)'
    POINT_PATTERN = r'^(\d+)\)'
    SUBSECTION_PATTERN = r'^([а-яіїєґ])\)'
    
    def __init__(self, chunk_size: int = None, overlap: float = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP
        self.encoding = tiktoken.encoding_for_model("gpt-4")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def find_structure_boundaries(self, text: str) -> List[Tuple[int, str, str]]:
        """
        Find structural boundaries in text
        
        Returns:
            List of (position, level, title) tuples
        """
        boundaries = []
        lines = text.split('\n')
        
        current_pos = 0
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for section
            match = re.match(self.SECTION_PATTERN, line_stripped, re.IGNORECASE)
            if match:
                boundaries.append((current_pos, "section", line_stripped))
            
            # Check for article
            match = re.match(self.ARTICLE_PATTERN, line_stripped, re.IGNORECASE)
            if match:
                boundaries.append((current_pos, "article", line_stripped))
            
            # Check for part
            match = re.match(self.PART_PATTERN, line_stripped, re.IGNORECASE)
            if match:
                boundaries.append((current_pos, "part", line_stripped))
            
            # Check for point
            match = re.match(self.POINT_PATTERN, line_stripped)
            if match:
                boundaries.append((current_pos, "point", line_stripped))
            
            current_pos += len(line) + 1  # +1 for newline
        
        return boundaries
    
    def chunk_by_structure(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk text by structure with overlap
        
        Returns:
            List of chunk dicts with metadata
        """
        boundaries = self.find_structure_boundaries(text)
        
        if not boundaries:
            # No structure found - use simple chunking
            return self.chunk_simple(text, doc_id, metadata)
        
        chunks = []
        current_section = None
        current_article = None
        current_part = None
        
        # Build section path as we go
        section_path = []
        
        i = 0
        while i < len(boundaries):
            start_pos = boundaries[i][0]
            
            # Determine end position
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][0]
            else:
                end_pos = len(text)
            
            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()
            
            if not chunk_text:
                i += 1
                continue
            
            # Update section path based on boundary level
            level = boundaries[i][1]
            title = boundaries[i][2]
            
            if level == "section":
                section_path = [title]
                current_section = title
            elif level == "article":
                if current_section:
                    section_path = [current_section, title]
                else:
                    section_path = [title]
                current_article = title
            elif level == "part":
                if current_article:
                    section_path = [current_section or "", current_article, title]
                elif current_section:
                    section_path = [current_section, title]
                else:
                    section_path = [title]
                current_part = title
            elif level == "point":
                if current_part:
                    section_path = [current_section or "", current_article or "", current_part, title]
                elif current_article:
                    section_path = [current_section or "", current_article, title]
                elif current_section:
                    section_path = [current_section, title]
                else:
                    section_path = [title]
            
            # Check if chunk is too large
            tokens = self.count_tokens(chunk_text)
            
            if tokens > self.chunk_size:
                # Split large chunk
                sub_chunks = self._split_large_chunk(
                    chunk_text,
                    doc_id,
                    metadata,
                    section_path,
                    start_pos
                )
                chunks.extend(sub_chunks)
            else:
                # Add chunk
                chunk_id = f"{doc_id}_chunk_{len(chunks)}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": chunk_text,
                    "metadata": {
                        **metadata,
                        "section_path": section_path.copy(),
                        "chunk_index": len(chunks),
                        "char_start": start_pos,
                        "char_end": start_pos + len(chunk_text),
                        "tokens": tokens,
                    }
                })
            
            i += 1
        
        # Add overlap between chunks
        if self.overlap > 0:
            chunks = self._add_overlap(chunks, text)
        
        return chunks
    
    def _split_large_chunk(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any],
        section_path: List[str],
        base_char_start: int
    ) -> List[Dict[str, Any]]:
        """Split a chunk that's too large"""
        chunks = []
        sentences = re.split(r'[.!?]\s+', text)
        
        current_chunk = ""
        current_tokens = 0
        chunk_start = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_id = f"{doc_id}_chunk_{len(chunks)}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "section_path": section_path.copy(),
                        "chunk_index": len(chunks),
                        "char_start": base_char_start + chunk_start,
                        "char_end": base_char_start + chunk_start + len(current_chunk),
                        "tokens": current_tokens,
                    }
                })
                
                # Start new chunk with overlap
                overlap_size = int(self.chunk_size * self.overlap)
                overlap_text = current_chunk[-overlap_size:] if len(current_chunk) > overlap_size else current_chunk
                current_chunk = overlap_text + " " + sentence
                current_tokens = self.count_tokens(current_chunk)
                chunk_start = base_char_start + len(current_chunk) - len(overlap_text) - len(sentence)
            else:
                current_chunk += sentence + ". "
                current_tokens += sentence_tokens + 2  # +2 for ". "
        
        # Add remaining chunk
        if current_chunk.strip():
            chunk_id = f"{doc_id}_chunk_{len(chunks)}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "text": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "section_path": section_path.copy(),
                    "chunk_index": len(chunks),
                    "char_start": base_char_start + chunk_start,
                    "char_end": base_char_start + chunk_start + len(current_chunk),
                    "tokens": current_tokens,
                }
            })
        
        return chunks
    
    def chunk_simple(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Simple chunking when no structure is found"""
        chunks = []
        sentences = re.split(r'[.!?]\s+', text)
        
        current_chunk = ""
        current_tokens = 0
        char_start = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save chunk
                chunk_id = f"{doc_id}_chunk_{len(chunks)}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "section_path": [],
                        "chunk_index": len(chunks),
                        "char_start": char_start,
                        "char_end": char_start + len(current_chunk),
                        "tokens": current_tokens,
                    }
                })
                
                # Start new chunk with overlap
                overlap_size = int(self.chunk_size * self.overlap)
                overlap_text = current_chunk[-overlap_size:] if len(current_chunk) > overlap_size else current_chunk
                current_chunk = overlap_text + " " + sentence
                current_tokens = self.count_tokens(current_chunk)
                char_start += len(current_chunk) - len(overlap_text) - len(sentence)
            else:
                current_chunk += sentence + ". "
                current_tokens += sentence_tokens + 2
        
        # Add remaining chunk
        if current_chunk.strip():
            chunk_id = f"{doc_id}_chunk_{len(chunks)}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "text": current_chunk.strip(),
                "metadata": {
                    **metadata,
                    "section_path": [],
                    "chunk_index": len(chunks),
                    "char_start": char_start,
                    "char_end": char_start + len(current_chunk),
                    "tokens": current_tokens,
                }
            })
        
        return chunks
    
    def _add_overlap(self, chunks: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
        """Add overlap between adjacent chunks"""
        if len(chunks) <= 1:
            return chunks
        
        overlap_chars = int(self.chunk_size * 0.25 * 4)  # Approximate chars for overlap tokens
        
        for i in range(len(chunks) - 1):
            current = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Get overlap text from end of current chunk
            current_text = current["text"]
            if len(current_text) > overlap_chars:
                overlap_text = current_text[-overlap_chars:]
                
                # Add to next chunk
                next_chunk["text"] = overlap_text + "\n\n" + next_chunk["text"]
                next_chunk["metadata"]["char_start"] = current["metadata"]["char_end"] - overlap_chars
        
        return chunks

