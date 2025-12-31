"""
Script to initialize database with categories
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.services.processing_service import ProcessingService


async def main():
    """Initialize database"""
    db = SessionLocal()
    try:
        processing_service = ProcessingService(db)
        await processing_service.initialize_categories()
        print("✅ Categories initialized successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

