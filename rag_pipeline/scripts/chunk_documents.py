#!/usr/bin/env python3
"""
CLI script: Chunk documents
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.chunking.splitter import StructuralChunker
from src.cleaning.cleaner import TextCleaner
from src.utils.config import settings
from tqdm import tqdm

setup_logging()
logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Chunk documents")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file")
    parser.add_argument("--output", type=str, required=True, help="Output JSONL file")
    parser.add_argument("--chunk-size", type=int, default=settings.CHUNK_SIZE, help="Chunk size in tokens")
    parser.add_argument("--overlap", type=float, default=settings.CHUNK_OVERLAP, help="Overlap ratio (0-1)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        logger.error("Input file does not exist", input_path=str(input_path))
        sys.exit(1)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    cleaner = TextCleaner()
    chunker = StructuralChunker(chunk_size=args.chunk_size, overlap=args.overlap)
    
    logger.info("Starting chunking", input=str(input_path), output=str(output_path))
    
    total_chunks = 0
    
    with open(input_path, "r", encoding="utf-8") as f_in, \
         open(output_path, "w", encoding="utf-8") as f_out:
        
        # Count lines for progress bar
        total_docs = sum(1 for _ in f_in)
        f_in.seek(0)
        
        for line in tqdm(f_in, total=total_docs, desc="Chunking"):
            doc = json.loads(line)
            
            # Clean text
            cleaned = cleaner.clean(doc["text"], extract_reference=True)
            
            # Update document metadata
            if cleaned["reference_block"]:
                doc["metadata"]["reference_block"] = cleaned["reference_block"]
            doc["metadata"].update(cleaned["metadata"])
            
            # Chunk text
            chunks = chunker.chunk_by_structure(
                text=cleaned["text"],
                doc_id=doc["doc_id"],
                metadata=doc["metadata"]
            )
            
            # Write chunks
            for chunk in chunks:
                f_out.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                total_chunks += 1
    
    logger.info("Chunking complete", total_chunks=total_chunks, output=str(output_path))


if __name__ == "__main__":
    main()




