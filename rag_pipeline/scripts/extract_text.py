#!/usr/bin/env python3
"""
CLI script: Extract text from files
"""
import argparse
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.ingestion.processor import extract_texts
from src.utils.config import settings

setup_logging()
logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Extract text from files")
    parser.add_argument("--input", type=str, required=True, help="Input file or directory")
    parser.add_argument("--output", type=str, required=True, help="Output JSONL file")
    parser.add_argument("--workers", type=int, default=settings.MAX_WORKERS, help="Number of workers")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        logger.error("Input path does not exist", input_path=str(input_path))
        sys.exit(1)
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting extraction", input=str(input_path), output=str(output_path))
    
    try:
        extract_texts(input_path, output_path, max_workers=args.workers)
        logger.info("Extraction complete", output=str(output_path))
    except Exception as e:
        logger.error("Extraction failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

