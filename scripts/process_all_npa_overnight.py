#!/usr/bin/env python3
"""
Скрипт для автоматичного завантаження та обробки ВСІХ НПА за ніч
Запускається один раз і обробляє всі доступні НПА з Rada API
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Set
import logging
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.legal_act import LegalAct
from app.services.rada_api import rada_api
from app.services.processing_service import ProcessingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overnight_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OvernightProcessor:
    """Автоматична обробка всіх НПА за ніч"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.processing_service = ProcessingService(self.db)
        self.stats = {
            "total_found": 0,
            "already_processed": 0,
            "successfully_processed": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": datetime.now()
        }
    
    async def get_all_nregs(self) -> List[str]:
        """Отримати всі NREG з Rada API"""
        logger.info("🔍 Отримання переліку всіх НПА з Rada API...")
        try:
            # Спочатку синхронізуємо список (створюємо записи в БД)
            logger.info("📥 Синхронізація списку НПА з Rada API...")
            all_nregs = await rada_api.get_all_documents_list(limit=None)
            
            if not all_nregs:
                logger.warning("⚠️ Не вдалося отримати список з Rada API, використовуємо список з БД")
                # Fallback: використовуємо NREG з бази даних
                acts = self.db.query(LegalAct.nreg).all()
                all_nregs = [act[0] for act in acts]
            
            logger.info(f"✅ Знайдено {len(all_nregs)} НПА")
            return all_nregs
        
        except Exception as e:
            logger.error(f"❌ Помилка отримання списку: {e}", exc_info=True)
            # Fallback: використовуємо NREG з бази даних
            acts = self.db.query(LegalAct.nreg).all()
            all_nregs = [act[0] for act in acts]
            logger.info(f"📦 Використовуємо {len(all_nregs)} НПА з бази даних")
            return all_nregs
    
    async def sync_all_nregs_to_db(self) -> int:
        """Синхронізувати всі NREG з Rada API в базу даних"""
        logger.info("🔄 Синхронізація всіх NREG з Rada API в базу даних...")
        
        try:
            all_nregs = await rada_api.get_all_documents_list(limit=None)
            
            if not all_nregs:
                logger.warning("⚠️ Не вдалося отримати список з Rada API")
                return 0
            
            existing_nregs = {act.nreg for act in self.db.query(LegalAct.nreg).all()}
            created = 0
            updated = 0
            
            for nreg in tqdm(all_nregs, desc="Синхронізація NREG"):
                try:
                    act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
                    
                    if act:
                        # Оновити title якщо відсутній
                        if not act.title or act.title == act.nreg:
                            try:
                                await rada_api._rate_limit()
                                card_json = await rada_api.get_document_card(nreg)
                                if card_json and card_json.get("title"):
                                    act.title = card_json.get("title")
                                    updated += 1
                            except:
                                pass
                    else:
                        # Створити новий запис
                        title = nreg
                        try:
                            await rada_api._rate_limit()
                            card_json = await rada_api.get_document_card(nreg)
                            if card_json and card_json.get("title"):
                                title = card_json.get("title")
                        except:
                            pass
                        
                        new_act = LegalAct(
                            nreg=nreg,
                            title=title,
                            is_processed=False
                        )
                        self.db.add(new_act)
                        created += 1
                    
                    # Commit every 100 acts
                    if (created + updated) % 100 == 0:
                        self.db.commit()
                
                except Exception as e:
                    logger.error(f"Помилка обробки NREG {nreg}: {e}")
                    self.db.rollback()
                    continue
            
            self.db.commit()
            logger.info(f"✅ Синхронізація завершена: {created} створено, {updated} оновлено")
            return len(all_nregs)
        
        except Exception as e:
            logger.error(f"❌ Помилка синхронізації: {e}", exc_info=True)
            return 0
    
    async def process_all_acts(self, batch_size: int = 10, delay_between_batches: float = 5.0):
        """
        Обробити всі НПА
        
        Args:
            batch_size: Кількість актів для обробки в одному батчі
            delay_between_batches: Затримка між батчами (секунди)
        """
        logger.info("🌙 Початок нічної обробки всіх НПА...")
        
        # Спочатку синхронізуємо список
        total_nregs = await self.sync_all_nregs_to_db()
        
        # Отримуємо всі NREG з бази даних
        all_acts = self.db.query(LegalAct).filter(LegalAct.is_processed == False).all()
        nregs_to_process = [act.nreg for act in all_acts]
        
        self.stats["total_found"] = len(nregs_to_process)
        logger.info(f"📊 Знайдено {len(nregs_to_process)} НПА для обробки")
        
        if not nregs_to_process:
            logger.info("✅ Всі НПА вже оброблені!")
            return
        
        # Обробляємо по батчах
        processed_count = 0
        failed_count = 0
        
        with tqdm(total=len(nregs_to_process), desc="Обробка НПА") as pbar:
            for i in range(0, len(nregs_to_process), batch_size):
                batch = nregs_to_process[i:i + batch_size]
                
                logger.info(f"📦 Обробка батча {i//batch_size + 1} ({len(batch)} актів)...")
                
                for nreg in batch:
                    try:
                        # Перевірка чи вже оброблено (на випадок паралельної обробки)
                        act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
                        if act and act.is_processed:
                            logger.info(f"⏭️  Акт {nreg} вже оброблено, пропускаємо")
                            self.stats["already_processed"] += 1
                            pbar.update(1)
                            continue
                        
                        # Обробка акту
                        logger.info(f"⚙️  Обробка акту {nreg}...")
                        result = await self.processing_service.process_legal_act(nreg)
                        
                        if result and result.is_processed:
                            self.db.commit()
                            processed_count += 1
                            self.stats["successfully_processed"] += 1
                            logger.info(f"✅ Акт {nreg} успішно оброблено ({processed_count}/{len(nregs_to_process)})")
                        else:
                            failed_count += 1
                            self.stats["failed"] += 1
                            logger.warning(f"❌ Не вдалося обробити акт {nreg}")
                        
                        pbar.update(1)
                    
                    except Exception as e:
                        failed_count += 1
                        self.stats["failed"] += 1
                        logger.error(f"❌ Помилка обробки акту {nreg}: {e}", exc_info=True)
                        self.db.rollback()
                        pbar.update(1)
                
                # Затримка між батчами
                if i + batch_size < len(nregs_to_process):
                    logger.info(f"⏸️  Затримка {delay_between_batches} секунд перед наступним батчем...")
                    await asyncio.sleep(delay_between_batches)
        
        # Фінальна статистика
        self.print_stats()
    
    def print_stats(self):
        """Вивести статистику обробки"""
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]
        
        logger.info("=" * 60)
        logger.info("📊 СТАТИСТИКА ОБРОБКИ")
        logger.info("=" * 60)
        logger.info(f"⏱️  Час виконання: {duration}")
        logger.info(f"📋 Всього знайдено: {self.stats['total_found']}")
        logger.info(f"✅ Успішно оброблено: {self.stats['successfully_processed']}")
        logger.info(f"⏭️  Вже були оброблені: {self.stats['already_processed']}")
        logger.info(f"❌ Помилок: {self.stats['failed']}")
        logger.info(f"📊 Успішність: {(self.stats['successfully_processed'] / max(self.stats['total_found'], 1) * 100):.1f}%")
        logger.info("=" * 60)
    
    def close(self):
        """Закрити з'єднання з БД"""
        self.db.close()


async def main():
    """Головна функція"""
    processor = OvernightProcessor()
    
    try:
        # Обробка всіх актів
        # batch_size=10 - обробляємо по 10 актів за раз
        # delay_between_batches=5.0 - затримка 5 секунд між батчами (для rate limiting)
        await processor.process_all_acts(
            batch_size=10,
            delay_between_batches=5.0
        )
    
    except KeyboardInterrupt:
        logger.info("⚠️  Обробку перервано користувачем")
        processor.print_stats()
    
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}", exc_info=True)
        processor.print_stats()
    
    finally:
        processor.close()


if __name__ == "__main__":
    print("🌙 Запуск нічної обробки всіх НПА...")
    print("=" * 60)
    asyncio.run(main())

