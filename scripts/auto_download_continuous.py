#!/usr/bin/env python3
"""
Неперервне автоматичне завантаження документів з Rada API
Працює в фоні, перевіряє нові документи періодично
"""
import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
import signal

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.legal_act import LegalAct
from app.services.rada_api import rada_api
from app.services.processing_service import ProcessingService
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_download_continuous.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown = False


def signal_handler(sig, frame):
    """Handle shutdown signal"""
    global shutdown
    logger.info("Shutdown signal received, finishing current batch...")
    shutdown = True


class ContinuousDownloader:
    """Неперервне завантаження з періодичною перевіркою"""
    
    def __init__(self, check_interval_hours: int = 24):
        self.db = SessionLocal()
        self.processing_service = ProcessingService(self.db)
        self.check_interval = timedelta(hours=check_interval_hours)
        self.last_check = None
    
    async def get_new_nregs(self) -> list:
        """Отримати нові NREG (за останні 30 днів)"""
        logger.info("Fetching new documents from Rada API...")
        nregs = await rada_api.get_new_documents_list(days=30)
        logger.info(f"Found {len(nregs)} new documents")
        return nregs
    
    async def process_nreg(self, nreg: str) -> bool:
        """Обробити один документ"""
        try:
            # Перевірка чи вже оброблено
            act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
            if act and act.is_processed:
                return True
            
            # Обробка
            result = await self.processing_service.process_legal_act(nreg)
            
            if result and result.is_processed:
                self.db.commit()
                return True
            else:
                logger.warning(f"Failed to process {nreg}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing {nreg}: {e}")
            self.db.rollback()
            return False
    
    async def process_batch(self, nregs: list, max_workers: int = 5):
        """Обробити батч"""
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(nreg: str):
            async with semaphore:
                return await self.process_nreg(nreg)
        
        tasks = [process_with_semaphore(nreg) for nreg in nregs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r is True)
        logger.info(f"Batch complete: {successful}/{len(nregs)} successful")
        return successful
    
    async def run_cycle(self, max_workers: int = 5):
        """Виконати один цикл перевірки та обробки"""
        global shutdown
        
        logger.info("=" * 80)
        logger.info(f"Starting check cycle at {datetime.now()}")
        
        # Отримати нові документи
        new_nregs = await self.get_new_nregs()
        
        if not new_nregs:
            logger.info("No new documents found")
            return
        
        # Фільтрувати вже оброблені
        to_process = []
        for nreg in new_nregs:
            if shutdown:
                break
            act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
            if not act or not act.is_processed:
                to_process.append(nreg)
        
        if not to_process:
            logger.info("All new documents already processed")
            return
        
        logger.info(f"Processing {len(to_process)} new documents...")
        
        # Обробка батчами
        batch_size = 50
        for i in range(0, len(to_process), batch_size):
            if shutdown:
                break
            
            batch = to_process[i:i + batch_size]
            await self.process_batch(batch, max_workers=max_workers)
            
            logger.info(f"Progress: {min(i + batch_size, len(to_process))}/{len(to_process)}")
        
        self.last_check = datetime.now()
        logger.info(f"Cycle complete at {datetime.now()}")
        logger.info("=" * 80)
    
    async def run(self, max_workers: int = 5):
        """Запустити неперервну обробку"""
        global shutdown
        
        logger.info("=" * 80)
        logger.info("Starting continuous downloader")
        logger.info(f"Check interval: {self.check_interval}")
        logger.info(f"Max workers: {max_workers}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Перший запуск одразу
        await self.run_cycle(max_workers=max_workers)
        
        # Далі періодично
        while not shutdown:
            try:
                # Чекати до наступної перевірки
                wait_seconds = self.check_interval.total_seconds()
                logger.info(f"Waiting {wait_seconds / 3600:.1f} hours until next check...")
                
                await asyncio.sleep(wait_seconds)
                
                if shutdown:
                    break
                
                # Виконати цикл
                await self.run_cycle(max_workers=max_workers)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cycle: {e}", exc_info=True)
                # Продовжити навіть при помилці
                await asyncio.sleep(300)  # 5 хвилин перед повтором
        
        logger.info("Continuous downloader stopped")
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous auto-download from Rada API")
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Check interval in hours (default: 24)"
    )
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Перевірка налаштувань
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set!")
        sys.exit(1)
    
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL not set!")
        sys.exit(1)
    
    downloader = ContinuousDownloader(check_interval_hours=args.interval)
    
    try:
        await downloader.run(max_workers=args.workers)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        downloader.db.close()


if __name__ == "__main__":
    asyncio.run(main())




