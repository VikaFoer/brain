#!/usr/bin/env python3
"""
Автоматичне завантаження та обробка всіх документів з Rada API
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Set
import logging
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.legal_act import LegalAct
from app.services.rada_api import rada_api
from app.services.processing_service import ProcessingService
from app.core.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoDownloader:
    """Автоматичне завантаження та обробка документів"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.processing_service = ProcessingService(self.db)
        self.processed_nregs: Set[str] = set()
        self.failed_nregs: Set[str] = set()
        self.stats = {
            "total": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "start_time": datetime.now()
        }
    
    def load_processed_nregs(self):
        """Завантажити список вже оброблених NREG з БД"""
        try:
            acts = self.db.query(LegalAct.nreg).filter(
                LegalAct.is_processed == True
            ).all()
            self.processed_nregs = {act[0] for act in acts}
            logger.info(f"Loaded {len(self.processed_nregs)} already processed documents")
        except Exception as e:
            logger.error(f"Error loading processed nregs: {e}")
    
    async def get_all_nregs(self) -> List[str]:
        """Отримати всі NREG з Rada API"""
        logger.info("Fetching all document NREGs from Rada API...")
        nregs = await rada_api.get_all_documents_list(limit=None)
        logger.info(f"Found {len(nregs)} total documents")
        return nregs
    
    async def process_nreg(self, nreg: str, progress_bar: tqdm = None) -> bool:
        """Обробити один документ"""
        try:
            # Перевірка чи вже оброблено
            if nreg in self.processed_nregs:
                self.stats["skipped"] += 1
                if progress_bar:
                    progress_bar.set_postfix({"status": f"Skipped: {self.stats['skipped']}"})
                return True
            
            # Обробка
            result = await self.processing_service.process_legal_act(nreg)
            
            if result and result.is_processed:
                self.processed_nregs.add(nreg)
                self.stats["processed"] += 1
                if progress_bar:
                    progress_bar.set_postfix({
                        "processed": self.stats["processed"],
                        "failed": self.stats["failed"]
                    })
                return True
            else:
                self.stats["failed"] += 1
                self.failed_nregs.add(nreg)
                logger.warning(f"Failed to process {nreg}")
                if progress_bar:
                    progress_bar.set_postfix({
                        "processed": self.stats["processed"],
                        "failed": self.stats["failed"]
                    })
                return False
                
        except Exception as e:
            self.stats["failed"] += 1
            self.failed_nregs.add(nreg)
            logger.error(f"Error processing {nreg}: {e}")
            if progress_bar:
                progress_bar.set_postfix({
                    "processed": self.stats["processed"],
                    "failed": self.stats["failed"]
                })
            return False
    
    async def process_batch(self, nregs: List[str], batch_size: int = 10):
        """Обробити батч документів з обмеженням паралельності"""
        semaphore = asyncio.Semaphore(batch_size)
        
        async def process_with_semaphore(nreg: str):
            async with semaphore:
                return await self.process_nreg(nreg)
        
        tasks = [process_with_semaphore(nreg) for nreg in nregs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def run(self, max_workers: int = 5, resume: bool = True):
        """Запустити автоматичне завантаження"""
        logger.info("=" * 80)
        logger.info("Starting automatic download and processing")
        logger.info("=" * 80)
        
        # Завантажити вже оброблені
        if resume:
            self.load_processed_nregs()
        
        # Отримати всі NREG
        all_nregs = await self.get_all_nregs()
        self.stats["total"] = len(all_nregs)
        
        # Фільтрувати вже оброблені
        nregs_to_process = [nreg for nreg in all_nregs if nreg not in self.processed_nregs]
        
        logger.info(f"Total documents: {self.stats['total']}")
        logger.info(f"Already processed: {len(self.processed_nregs)}")
        logger.info(f"To process: {len(nregs_to_process)}")
        logger.info(f"Max workers: {max_workers}")
        logger.info("-" * 80)
        
        if not nregs_to_process:
            logger.info("All documents already processed!")
            return
        
        # Обробка з прогрес-баром
        with tqdm(total=len(nregs_to_process), desc="Processing documents") as pbar:
            # Обробляємо батчами для кращого контролю
            batch_size = 50  # Розмір батчу для відображення прогресу
            for i in range(0, len(nregs_to_process), batch_size):
                batch = nregs_to_process[i:i + batch_size]
                
                # Обробка батчу з обмеженням паралельності
                await self.process_batch(batch, batch_size=max_workers)
                
                pbar.update(len(batch))
                
                # Коміт після кожного батчу
                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    self.db.rollback()
                
                # Логування прогресу
                if (i + batch_size) % 100 == 0:
                    elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
                    rate = self.stats["processed"] / elapsed if elapsed > 0 else 0
                    remaining = len(nregs_to_process) - i - batch_size
                    eta_seconds = remaining / rate if rate > 0 else 0
                    eta_hours = eta_seconds / 3600
                    
                    logger.info(
                        f"Progress: {i + batch_size}/{len(nregs_to_process)} "
                        f"({(i + batch_size) / len(nregs_to_process) * 100:.1f}%) | "
                        f"Processed: {self.stats['processed']} | "
                        f"Failed: {self.stats['failed']} | "
                        f"Rate: {rate:.2f} docs/sec | "
                        f"ETA: {eta_hours:.1f} hours"
                    )
        
        # Фінальна статистика
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        elapsed_hours = elapsed / 3600
        
        logger.info("=" * 80)
        logger.info("Processing complete!")
        logger.info(f"Total documents: {self.stats['total']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Skipped (already processed): {self.stats['skipped']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Time elapsed: {elapsed_hours:.2f} hours")
        logger.info(f"Average rate: {self.stats['processed'] / elapsed:.2f} docs/sec" if elapsed > 0 else "N/A")
        
        if self.failed_nregs:
            logger.warning(f"Failed NREGs ({len(self.failed_nregs)}): {list(self.failed_nregs)[:10]}...")
            # Зберегти failed nregs у файл
            with open("failed_nregs.txt", "w") as f:
                for nreg in self.failed_nregs:
                    f.write(f"{nreg}\n")
            logger.info("Failed NREGs saved to failed_nregs.txt")
        
        logger.info("=" * 80)
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db'):
            self.db.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-download and process all documents from Rada API")
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't skip already processed documents"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of documents to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Перевірка налаштувань
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set! Please configure it in .env")
        sys.exit(1)
    
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL not set! Please configure it in .env")
        sys.exit(1)
    
    # Створити downloader
    downloader = AutoDownloader()
    
    try:
        # Запустити обробку
        await downloader.run(
            max_workers=args.workers,
            resume=not args.no_resume
        )
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Saving progress...")
        logger.info(f"Processed: {downloader.stats['processed']}")
        logger.info(f"Failed: {downloader.stats['failed']}")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        downloader.db.close()


if __name__ == "__main__":
    asyncio.run(main())




