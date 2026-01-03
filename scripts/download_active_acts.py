#!/usr/bin/env python3
"""
Скрипт для завантаження всіх ДІЮЧИХ нормативно-правових актів
Фільтрує тільки акти зі статусом "діє" або подібним
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Set, Optional
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
        logging.FileHandler('download_active_acts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Статуси, які вважаються "діючими"
ACTIVE_STATUSES = [
    "діє",
    "діючий",
    "в дії",
    "чинний",
    "active",
    "valid",
    "в силі",
    None  # Якщо статус не вказано, вважаємо діючим
]


def is_active_status(status: Optional[str]) -> bool:
    """Перевірити, чи статус вказує на діючий акт"""
    if status is None:
        return True  # Якщо статус не вказано, вважаємо діючим
    
    status_lower = str(status).lower().strip()
    
    # Перевірка на діючі статуси
    for active_status in ACTIVE_STATUSES:
        if active_status and active_status.lower() in status_lower:
            return True
    
    # Перевірка на недіючі статуси
    inactive_keywords = ["втратив", "скасовано", "недійсний", "застарілий", "втратив чинність"]
    for keyword in inactive_keywords:
        if keyword in status_lower:
            return False
    
    # Якщо не знайдено явних індикаторів, вважаємо діючим
    return True


class ActiveActsDownloader:
    """Завантаження та обробка тільки діючих НПА"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.processing_service = ProcessingService(self.db)
        self.processed_nregs: Set[str] = set()
        self.failed_nregs: Set[str] = set()
        self.active_nregs: List[str] = []
        self.stats = {
            "total": 0,
            "active": 0,
            "inactive": 0,
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
            logger.info(f"Завантажено {len(self.processed_nregs)} вже оброблених документів")
        except Exception as e:
            logger.error(f"Помилка завантаження оброблених NREG: {e}")
    
    async def get_all_nregs(self) -> List[str]:
        """Отримати всі NREG з Rada API"""
        logger.info("Отримання всіх NREG з Rada API...")
        
        # Спробувати open data API спочатку
        try:
            logger.info("Спроба отримати через open data portal API...")
            nregs = await rada_api.get_all_nregs_from_open_data()
            if nregs:
                logger.info(f"✅ Отримано {len(nregs)} NREG через open data portal")
                return nregs
        except Exception as e:
            logger.warning(f"Open data API не працює: {e}")
        
        # Fallback до звичайного методу
        logger.info("Використання стандартного методу...")
        nregs = await rada_api.get_all_documents_list(limit=None)
        logger.info(f"Знайдено {len(nregs)} документів")
        return nregs
    
    async def filter_active_acts(self, nregs: List[str]) -> List[str]:
        """Фільтрувати тільки діючі акти"""
        logger.info(f"Фільтрація діючих актів з {len(nregs)} загальних...")
        
        active_nregs = []
        batch_size = 50  # Перевіряємо батчами для швидкості
        
        for i in range(0, len(nregs), batch_size):
            batch = nregs[i:i + batch_size]
            
            for nreg in batch:
                try:
                    # Отримати картку документа для перевірки статусу
                    card = await rada_api.get_document_card(nreg)
                    
                    if card:
                        status = card.get("status") or card.get("Статус") or card.get("статус")
                        
                        if is_active_status(status):
                            active_nregs.append(nreg)
                            self.stats["active"] += 1
                        else:
                            self.stats["inactive"] += 1
                            logger.debug(f"Пропущено недіючий акт {nreg}: {status}")
                    else:
                        # Якщо не вдалося отримати картку, вважаємо діючим
                        active_nregs.append(nreg)
                        self.stats["active"] += 1
                        logger.debug(f"Не вдалося отримати статус для {nreg}, вважаємо діючим")
                
                except Exception as e:
                    logger.warning(f"Помилка перевірки статусу для {nreg}: {e}")
                    # У разі помилки вважаємо діючим
                    active_nregs.append(nreg)
                    self.stats["active"] += 1
            
            # Логування прогресу
            if (i + batch_size) % 500 == 0:
                logger.info(f"Перевірено {min(i + batch_size, len(nregs))}/{len(nregs)} актів. Діючих: {len(active_nregs)}")
        
        logger.info(f"✅ Фільтрація завершена: {len(active_nregs)} діючих з {len(nregs)} загальних")
        return active_nregs
    
    async def process_nreg(self, nreg: str, progress_bar: tqdm = None) -> bool:
        """Обробити один документ"""
        try:
            # Перевірка чи вже оброблено
            if nreg in self.processed_nregs:
                self.stats["skipped"] += 1
                if progress_bar:
                    progress_bar.set_postfix({"status": f"Пропущено: {self.stats['skipped']}"})
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
                logger.warning(f"Не вдалося обробити {nreg}")
                if progress_bar:
                    progress_bar.set_postfix({
                        "processed": self.stats["processed"],
                        "failed": self.stats["failed"]
                    })
                return False
                
        except Exception as e:
            self.stats["failed"] += 1
            self.failed_nregs.add(nreg)
            logger.error(f"Помилка обробки {nreg}: {e}")
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
    
    async def run(self, max_workers: int = 5, filter_active: bool = True, resume: bool = True):
        """Запустити завантаження діючих НПА"""
        logger.info("=" * 80)
        logger.info("Завантаження ДІЮЧИХ нормативно-правових актів")
        logger.info("=" * 80)
        
        # Завантажити вже оброблені
        if resume:
            self.load_processed_nregs()
        
        # Отримати всі NREG
        all_nregs = await self.get_all_nregs()
        self.stats["total"] = len(all_nregs)
        
        # Фільтрувати діючі
        if filter_active:
            active_nregs = await self.filter_active_acts(all_nregs)
        else:
            active_nregs = all_nregs
            self.stats["active"] = len(active_nregs)
        
        # Фільтрувати вже оброблені
        nregs_to_process = [nreg for nreg in active_nregs if nreg not in self.processed_nregs]
        
        logger.info(f"Всього документів: {self.stats['total']}")
        logger.info(f"Діючих: {self.stats['active']}")
        logger.info(f"Недіючих: {self.stats['inactive']}")
        logger.info(f"Вже оброблено: {len(self.processed_nregs)}")
        logger.info(f"До обробки: {len(nregs_to_process)}")
        logger.info(f"Паралельних воркерів: {max_workers}")
        logger.info("-" * 80)
        
        if not nregs_to_process:
            logger.info("Всі діючі документи вже оброблено!")
            return
        
        # Обробка з прогрес-баром
        with tqdm(total=len(nregs_to_process), desc="Обробка діючих НПА") as pbar:
            batch_size = 50
            for i in range(0, len(nregs_to_process), batch_size):
                batch = nregs_to_process[i:i + batch_size]
                
                await self.process_batch(batch, batch_size=max_workers)
                pbar.update(len(batch))
                
                # Коміт після кожного батчу
                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Помилка коміту батчу: {e}")
                    self.db.rollback()
                
                # Логування прогресу
                if (i + batch_size) % 100 == 0:
                    elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
                    rate = self.stats["processed"] / elapsed if elapsed > 0 else 0
                    remaining = len(nregs_to_process) - i - batch_size
                    eta_seconds = remaining / rate if rate > 0 else 0
                    eta_hours = eta_seconds / 3600
                    
                    logger.info(
                        f"Прогрес: {i + batch_size}/{len(nregs_to_process)} "
                        f"({(i + batch_size) / len(nregs_to_process) * 100:.1f}%) | "
                        f"Оброблено: {self.stats['processed']} | "
                        f"Помилок: {self.stats['failed']} | "
                        f"Швидкість: {rate:.2f} док/сек | "
                        f"Залишилось: {eta_hours:.1f} год"
                    )
        
        # Фінальна статистика
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        elapsed_hours = elapsed / 3600
        
        logger.info("=" * 80)
        logger.info("Обробка завершена!")
        logger.info(f"Всього документів: {self.stats['total']}")
        logger.info(f"Діючих: {self.stats['active']}")
        logger.info(f"Недіючих: {self.stats['inactive']}")
        logger.info(f"Оброблено: {self.stats['processed']}")
        logger.info(f"Пропущено (вже оброблено): {self.stats['skipped']}")
        logger.info(f"Помилок: {self.stats['failed']}")
        logger.info(f"Час виконання: {elapsed_hours:.2f} годин")
        logger.info(f"Середня швидкість: {self.stats['processed'] / elapsed:.2f} док/сек" if elapsed > 0 else "N/A")
        
        if self.failed_nregs:
            logger.warning(f"Помилкові NREG ({len(self.failed_nregs)}): {list(self.failed_nregs)[:10]}...")
            with open("failed_active_nregs.txt", "w", encoding="utf-8") as f:
                for nreg in self.failed_nregs:
                    f.write(f"{nreg}\n")
            logger.info("Помилкові NREG збережено в failed_active_nregs.txt")
        
        logger.info("=" * 80)
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db'):
            self.db.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Завантажити та обробити всі діючі НПА")
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Кількість паралельних воркерів (за замовчуванням: 5)"
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Не фільтрувати за статусом (завантажити всі)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Не пропускати вже оброблені документи"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Обмежити кількість документів для обробки (для тестування)"
    )
    
    args = parser.parse_args()
    
    # Перевірка налаштувань
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY не встановлено! Налаштуйте в .env")
        sys.exit(1)
    
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL не встановлено! Налаштуйте в .env")
        sys.exit(1)
    
    # Створити downloader
    downloader = ActiveActsDownloader()
    
    try:
        # Запустити обробку
        await downloader.run(
            max_workers=args.workers,
            filter_active=not args.no_filter,
            resume=not args.no_resume
        )
    except KeyboardInterrupt:
        logger.info("\nПерервано користувачем. Збереження прогресу...")
        logger.info(f"Оброблено: {downloader.stats['processed']}")
        logger.info(f"Помилок: {downloader.stats['failed']}")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        downloader.db.close()


if __name__ == "__main__":
    asyncio.run(main())

