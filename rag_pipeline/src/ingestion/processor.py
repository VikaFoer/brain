"""
Process files and generate JSONL output
"""
import json
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import structlog
from src.ingestion.extractors import FileExtractor
from src.utils.config import settings

logger = structlog.get_logger(__name__)


def generate_doc_id(file_path: Path, metadata: Dict[str, Any]) -> str:
    """Generate unique document ID"""
    # Use file path + modification time for uniqueness
    mtime = file_path.stat().st_mtime
    content = f"{file_path}_{mtime}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def process_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Process a single file and return document dict"""
    try:
        result = FileExtractor.extract(file_path)
        text = result["text"]
        metadata = result["metadata"]
        
        # Skip if needs OCR
        if metadata.get("needs_ocr", False):
            logger.warning("Skipping file (needs OCR)", file_path=str(file_path))
            return None
        
        # Skip if too short
        if len(text.strip()) < 100:
            logger.warning("Skipping file (too short)", file_path=str(file_path))
            return None
        
        # Generate document ID
        doc_id = generate_doc_id(file_path, metadata)
        
        # Build document
        document = {
            "doc_id": doc_id,
            "metadata": {
                **metadata,
                "text_length": len(text),
            },
            "text": text,
        }
        
        logger.info("Processed file", doc_id=doc_id, file_path=str(file_path))
        return document
        
    except Exception as e:
        logger.error("Failed to process file", file_path=str(file_path), error=str(e))
        return None


def extract_texts(input_path: Path, output_path: Path, max_workers: int = None):
    """
    Extract text from files and write to JSONL
    
    Args:
        input_path: Path to file or directory
        output_path: Path to output JSONL file
        max_workers: Number of parallel workers
    """
    max_workers = max_workers or settings.MAX_WORKERS
    
    # Collect files
    files = []
    if input_path.is_file():
        files.append(input_path)
    elif input_path.is_dir():
        for ext in [".pdf", ".html", ".htm", ".docx", ".txt"]:
            files.extend(input_path.rglob(f"*{ext}"))
    else:
        raise ValueError(f"Invalid input path: {input_path}")
    
    logger.info("Starting extraction", total_files=len(files), workers=max_workers)
    
    # Process files in parallel
    with open(output_path, "w", encoding="utf-8") as f_out:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, file_path): file_path for file_path in files}
            
            processed = 0
            failed = 0
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
                    processed += 1
                else:
                    failed += 1
                
                if (processed + failed) % 100 == 0:
                    logger.info("Progress", processed=processed, failed=failed, total=len(files))
    
    logger.info("Extraction complete", processed=processed, failed=failed, total=len(files))

