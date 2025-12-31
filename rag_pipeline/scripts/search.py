#!/usr/bin/env python3
"""
CLI script: Search for similar chunks
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging, get_logger
from src.retrieval.searcher import Searcher
from src.utils.config import settings

setup_logging()
logger = get_logger(__name__)


async def search(query: str, topk: int, threshold: float):
    """Perform search"""
    searcher = Searcher()
    results = await searcher.search(
        query=query,
        topk=topk,
        similarity_threshold=threshold
    )
    
    # Print results
    print(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [Similarity: {result['similarity']:.3f}]")
        print(f"   Document: {result['document'].get('title', 'N/A')}")
        print(f"   Act: {result['document'].get('act_number', 'N/A')}")
        print(f"   Section: {' → '.join(result.get('section_path', []))}")
        print(f"   Text: {result['text'][:200]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Search for similar chunks")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    parser.add_argument("--topk", type=int, default=settings.TOPK, help="Number of results")
    parser.add_argument("--threshold", type=float, default=settings.SIMILARITY_THRESHOLD, help="Similarity threshold")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    try:
        searcher = Searcher()
        results = asyncio.run(searcher.search(
            query=args.query,
            topk=args.topk,
            similarity_threshold=args.threshold
        ))
        
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"\nFound {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. [Similarity: {result['similarity']:.3f}]")
                print(f"   Document: {result['document'].get('title', 'N/A')}")
                print(f"   Act: {result['document'].get('act_number', 'N/A')}")
                print(f"   Section: {' → '.join(result.get('section_path', []))}")
                print(f"   Text: {result['text'][:200]}...")
                print()
    except Exception as e:
        logger.error("Search failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

