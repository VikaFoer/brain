"""
Data Access Object for PostgreSQL + pgvector
"""
from typing import List, Dict, Any, Optional
import psycopg
from psycopg.types.json import Json
import structlog
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class VectorDAO:
    """Data Access Object for vector storage"""
    
    def __init__(self, connection_string: str = None):
        self.conn_string = connection_string or settings.DATABASE_URL
    
    def _get_connection(self):
        """Get database connection"""
        return psycopg.connect(self.conn_string)
    
    def insert_document(self, doc: Dict[str, Any]) -> bool:
        """Insert or update document"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (
                            doc_id, title, act_number, date, authority,
                            url, source, file_type, file_path, text_length,
                            needs_ocr, reference_block, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (doc_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            act_number = EXCLUDED.act_number,
                            date = EXCLUDED.date,
                            authority = EXCLUDED.authority,
                            url = EXCLUDED.url,
                            source = EXCLUDED.source,
                            file_type = EXCLUDED.file_type,
                            file_path = EXCLUDED.file_path,
                            text_length = EXCLUDED.text_length,
                            needs_ocr = EXCLUDED.needs_ocr,
                            reference_block = EXCLUDED.reference_block,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """, (
                        doc["doc_id"],
                        doc.get("metadata", {}).get("title"),
                        doc.get("metadata", {}).get("act_number"),
                        doc.get("metadata", {}).get("date"),
                        doc.get("metadata", {}).get("authority"),
                        doc.get("metadata", {}).get("url"),
                        doc.get("metadata", {}).get("source"),
                        doc.get("metadata", {}).get("file_type"),
                        doc.get("metadata", {}).get("file_path"),
                        doc.get("metadata", {}).get("text_length"),
                        doc.get("metadata", {}).get("needs_ocr", False),
                        doc.get("metadata", {}).get("reference_block"),
                        Json(doc.get("metadata", {}))
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error("Failed to insert document", doc_id=doc.get("doc_id"), error=str(e))
            return False
    
    def insert_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Insert or update chunk with embedding"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if chunk already exists (idempotency)
                    cur.execute("SELECT chunk_id FROM chunks WHERE chunk_id = %s", (chunk["chunk_id"],))
                    if cur.fetchone():
                        logger.debug("Chunk already exists, skipping", chunk_id=chunk["chunk_id"])
                        return True
                    
                    # Insert chunk
                    cur.execute("""
                        INSERT INTO chunks (
                            chunk_id, doc_id, chunk_text, embedding,
                            section_path, chunk_index, char_start, char_end,
                            tokens, metadata
                        ) VALUES (
                            %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        chunk["chunk_id"],
                        chunk["doc_id"],
                        chunk["text"],
                        chunk.get("embedding"),  # Will be converted to vector type
                        chunk.get("metadata", {}).get("section_path", []),
                        chunk.get("metadata", {}).get("chunk_index"),
                        chunk.get("metadata", {}).get("char_start"),
                        chunk.get("metadata", {}).get("char_end"),
                        chunk.get("metadata", {}).get("tokens"),
                        Json(chunk.get("metadata", {}))
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error("Failed to insert chunk", chunk_id=chunk.get("chunk_id"), error=str(e))
            return False
    
    def insert_chunks_batch(self, chunks: List[Dict[str, Any]]) -> int:
        """Insert chunks in batch (more efficient)"""
        successful = 0
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check existing chunks for idempotency
                    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
                    cur.execute(
                        "SELECT chunk_id FROM chunks WHERE chunk_id = ANY(%s)",
                        (chunk_ids,)
                    )
                    existing = {row[0] for row in cur.fetchall()}
                    
                    # Filter out existing chunks
                    new_chunks = [c for c in chunks if c["chunk_id"] not in existing]
                    
                    if not new_chunks:
                        logger.info("All chunks already exist", total=len(chunks))
                        return len(chunks)
                    
                    # Insert new chunks
                    for chunk in new_chunks:
                        try:
                            cur.execute("""
                                INSERT INTO chunks (
                                    chunk_id, doc_id, chunk_text, embedding,
                                    section_path, chunk_index, char_start, char_end,
                                    tokens, metadata
                                ) VALUES (
                                    %s, %s, %s, %s::vector, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                chunk["chunk_id"],
                                chunk["doc_id"],
                                chunk["text"],
                                chunk.get("embedding"),
                                chunk.get("metadata", {}).get("section_path", []),
                                chunk.get("metadata", {}).get("chunk_index"),
                                chunk.get("metadata", {}).get("char_start"),
                                chunk.get("metadata", {}).get("char_end"),
                                chunk.get("metadata", {}).get("tokens"),
                                Json(chunk.get("metadata", {}))
                            ))
                            successful += 1
                        except Exception as e:
                            logger.warning("Failed to insert chunk", chunk_id=chunk.get("chunk_id"), error=str(e))
                    
                    conn.commit()
                    logger.info("Batch insert complete", successful=successful, total=len(chunks))
                    return successful
        except Exception as e:
            logger.error("Failed batch insert", error=str(e))
            return successful
    
    def search_similar(
        self,
        query_embedding: List[float],
        topk: int = 10,
        similarity_threshold: float = 0.7,
        doc_id: Optional[str] = None,
        section_path: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using cosine similarity
        
        Args:
            query_embedding: Query embedding vector
            topk: Number of results
            similarity_threshold: Minimum similarity score
            doc_id: Filter by document ID (optional)
            section_path: Filter by section path (optional)
        
        Returns:
            List of chunks with similarity scores
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Build query
                    query = """
                        SELECT 
                            c.chunk_id,
                            c.doc_id,
                            c.chunk_text,
                            c.section_path,
                            c.chunk_index,
                            c.char_start,
                            c.char_end,
                            c.metadata,
                            d.title,
                            d.act_number,
                            d.date,
                            d.authority,
                            d.url,
                            1 - (c.embedding <=> %s::vector) as similarity
                        FROM chunks c
                        JOIN documents d ON c.doc_id = d.doc_id
                        WHERE c.embedding IS NOT NULL
                    """
                    
                    params = [query_embedding]
                    
                    # Add filters
                    if doc_id:
                        query += " AND c.doc_id = %s"
                        params.append(doc_id)
                    
                    if section_path:
                        query += " AND c.section_path @> %s"
                        params.append(section_path)
                    
                    # Add similarity threshold and ordering
                    query += """
                        AND (1 - (c.embedding <=> %s::vector)) >= %s
                        ORDER BY c.embedding <=> %s::vector
                        LIMIT %s
                    """
                    params.extend([query_embedding, similarity_threshold, query_embedding, topk])
                    
                    cur.execute(query, params)
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            "chunk_id": row[0],
                            "doc_id": row[1],
                            "text": row[2],
                            "section_path": row[3],
                            "chunk_index": row[4],
                            "char_start": row[5],
                            "char_end": row[6],
                            "metadata": row[7],
                            "document": {
                                "title": row[8],
                                "act_number": row[9],
                                "date": row[10],
                                "authority": row[11],
                                "url": row[12],
                            },
                            "similarity": float(row[13]),
                        })
                    
                    return results
        except Exception as e:
            logger.error("Search failed", error=str(e))
            return []




