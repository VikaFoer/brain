#!/usr/bin/env python3
"""
CLI script: Generate embeddings and store in database
"""
import argparse
import json
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.embeddings.generator import EmbeddingsGenerator
from src.storage.dao import VectorDAO
from src.utils.config import settings
from tqdm import tqdm

setup_logging()
logger = get_logger(__name__)


async def process_chunks(input_path: Path, batch_size: int = None):
    """Process chunks: generate embeddings and store"""
    batch_size = batch_size or settings.BATCH_SIZE
    
    embeddings_gen = EmbeddingsGenerator()
    dao = VectorDAO()
    
    # Read all chunks
    chunks = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            chunk = json.loads(line)
            chunks.append(chunk)
    
    logger.info("Starting embeddings generation", total_chunks=len(chunks))
    
    # Generate embeddings
    embedded_chunks = await embeddings_gen.generate_embeddings(chunks)
    
    # Filter successful embeddings
    successful_chunks = [c for c in embedded_chunks if c.get("embedding") is not None]
    failed_chunks = [c for c in embedded_chunks if c.get("embedding") is None]
    
    logger.info("Embeddings generated", successful=len(successful_chunks), failed=len(failed_chunks))
    
    # Store in database
    logger.info("Storing chunks in database")
    
    # First, insert documents (if not exists)
    doc_ids = set(c["doc_id"] for c in successful_chunks)
    for doc_id in tqdm(doc_ids, desc="Inserting documents"):
        # Find first chunk with this doc_id to get doc metadata
        chunk = next(c for c in successful_chunks if c["doc_id"] == doc_id)
        doc_metadata = chunk.get("metadata", {})
        
        # Create document record
        doc = {
            "doc_id": doc_id,
            "metadata": {
                **doc_metadata,
                "title": doc_metadata.get("title"),
                "act_number": doc_metadata.get("act_number"),
                "date": doc_metadata.get("date"),
                "authority": doc_metadata.get("authority"),
                "url": doc_metadata.get("url"),
                "source": doc_metadata.get("source"),
                "file_type": doc_metadata.get("file_type"),
                "file_path": doc_metadata.get("file_path"),
                "text_length": doc_metadata.get("text_length"),
            }
        }
        dao.insert_document(doc)
    
    # Insert chunks in batches
    total_inserted = 0
    for i in tqdm(range(0, len(successful_chunks), batch_size), desc="Inserting chunks"):
        batch = successful_chunks[i:i + batch_size]
        inserted = dao.insert_chunks_batch(batch)
        total_inserted += inserted
    
    logger.info("Storage complete", total_inserted=total_inserted, total_chunks=len(successful_chunks))


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings and store")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file with chunks")
    parser.add_argument("--batch-size", type=int, default=settings.BATCH_SIZE, help="Batch size for embeddings")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error("Input file does not exist", input_path=str(input_path))
        sys.exit(1)
    
    logger.info("Starting embedding and storage", input=str(input_path))
    
    try:
        asyncio.run(process_chunks(input_path, batch_size=args.batch_size))
        logger.info("Complete")
    except Exception as e:
        logger.error("Failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

