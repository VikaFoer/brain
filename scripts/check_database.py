#!/usr/bin/env python3
"""
Перевірка налаштування бази даних
"""
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import engine, SessionLocal, Base
from app.models.legal_act import LegalAct
from app.models.category import Category
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection():
    """Перевірка підключення до бази даних"""
    print("=" * 80)
    print("1. ПЕРЕВІРКА ПІДКЛЮЧЕННЯ ДО БАЗИ ДАНИХ")
    print("=" * 80)
    
    # Перевірка DATABASE_URL
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL не встановлено!")
        print("   Додайте DATABASE_URL в .env файл")
        return False
    
    database_url = settings.DATABASE_URL
    is_sqlite = database_url.startswith("sqlite")
    
    if is_sqlite:
        print("⚠️  ВИКОРИСТОВУЄТЬСЯ SQLite!")
        print("   SQLite не підходить для production - дані будуть втрачені на Railway")
        print("   Рекомендовано: використати PostgreSQL")
    else:
        print("✅ Використовується PostgreSQL")
        # Приховати пароль у виводі
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(database_url)
            if parsed.password:
                safe_netloc = f"{parsed.username}:***@{parsed.hostname}"
                if parsed.port:
                    safe_netloc += f":{parsed.port}"
                safe_url = urlunparse(parsed._replace(netloc=safe_netloc))
                print(f"   URL: {safe_url}")
            else:
                print(f"   URL: {database_url[:50]}...")
        except:
            print(f"   URL: встановлено (пароль приховано)")
    
    # Перевірка підключення
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Підключення до бази даних успішне")
        return True
    except OperationalError as e:
        print(f"❌ Помилка підключення: {e}")
        return False
    except Exception as e:
        print(f"❌ Невідома помилка: {e}")
        return False


def check_tables():
    """Перевірка наявності таблиць"""
    print("\n" + "=" * 80)
    print("2. ПЕРЕВІРКА ТАБЛИЦЬ")
    print("=" * 80)
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = [
            "categories",
            "subsets",
            "legal_acts",
            "act_categories",
            "act_relations"
        ]
        
        print(f"Знайдено таблиць: {len(tables)}")
        
        all_exist = True
        for table in required_tables:
            if table in tables:
                print(f"✅ {table}")
            else:
                print(f"❌ {table} - відсутня!")
                all_exist = False
        
        if all_exist:
            print("\n✅ Всі необхідні таблиці існують")
        else:
            print("\n⚠️  Деякі таблиці відсутні. Запустіть міграції або створіть таблиці.")
            print("   Можна використати: python scripts/init_db.py")
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Помилка перевірки таблиць: {e}")
        return False


def check_pgvector():
    """Перевірка pgvector extension (тільки для PostgreSQL)"""
    print("\n" + "=" * 80)
    print("3. ПЕРЕВІРКА PGVECTOR (для RAG pipeline)")
    print("=" * 80)
    
    database_url = settings.DATABASE_URL or ""
    if database_url.startswith("sqlite"):
        print("⚠️  SQLite - pgvector не підтримується")
        print("   pgvector працює тільки з PostgreSQL")
        return False
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            if result.fetchone():
                print("✅ pgvector extension встановлено")
                return True
            else:
                print("⚠️  pgvector extension не встановлено")
                print("   Для RAG pipeline потрібен pgvector")
                print("   Встановіть: CREATE EXTENSION IF NOT EXISTS vector;")
                return False
    except Exception as e:
        print(f"⚠️  Не вдалося перевірити pgvector: {e}")
        return False


def check_data():
    """Перевірка даних у базі"""
    print("\n" + "=" * 80)
    print("4. СТАТИСТИКА ДАНИХ")
    print("=" * 80)
    
    try:
        db = SessionLocal()
        
        # Категорії
        categories_count = db.query(Category).count()
        print(f"Категорії: {categories_count}")
        if categories_count == 0:
            print("   ⚠️  Категорії не ініціалізовані")
            print("   Запустіть: GET /api/legal-acts/initialize-categories")
        else:
            print("   ✅ Категорії ініціалізовані")
        
        # Документи
        acts_count = db.query(LegalAct).count()
        processed_count = db.query(LegalAct).filter(LegalAct.is_processed == True).count()
        with_embeddings = db.query(LegalAct).filter(LegalAct.embeddings.isnot(None)).count()
        
        print(f"\nДокументи:")
        print(f"   Всього: {acts_count}")
        print(f"   Оброблено: {processed_count}")
        print(f"   З embeddings: {with_embeddings}")
        
        if acts_count > 0:
            percentage = (processed_count / acts_count * 100) if acts_count > 0 else 0
            print(f"   Прогрес: {percentage:.1f}%")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Помилка перевірки даних: {e}")
        return False


def check_config():
    """Перевірка конфігурації"""
    print("\n" + "=" * 80)
    print("5. ПЕРЕВІРКА КОНФІГУРАЦІЇ")
    print("=" * 80)
    
    checks = []
    
    # OpenAI
    if settings.OPENAI_API_KEY:
        print("✅ OPENAI_API_KEY встановлено")
        print(f"   Модель: {settings.OPENAI_MODEL}")
        print(f"   Embeddings: {settings.OPENAI_EMBED_MODEL}")
        checks.append(True)
    else:
        print("❌ OPENAI_API_KEY не встановлено")
        print("   Додайте OPENAI_API_KEY в .env")
        checks.append(False)
    
    # Rada API
    print(f"\nRada API:")
    print(f"   Base URL: {settings.RADA_API_BASE_URL}")
    print(f"   Rate limit: {settings.RADA_API_RATE_LIMIT} req/min")
    print(f"   Delay: {settings.RADA_API_DELAY} сек")
    if settings.RADA_API_TOKEN:
        print("   ✅ Token встановлено")
    else:
        print("   ⚠️  Token не встановлено (буде отримано автоматично)")
    
    # Neo4j
    print(f"\nNeo4j:")
    if settings.NEO4J_PASSWORD:
        print(f"   ✅ Налаштовано: {settings.NEO4J_URI}")
    else:
        print("   ⚠️  Не налаштовано (опціонально)")
    
    return all(checks)


def check_table_structure():
    """Перевірка структури таблиць"""
    print("\n" + "=" * 80)
    print("6. СТРУКТУРА ТАБЛИЦЬ")
    print("=" * 80)
    
    try:
        inspector = inspect(engine)
        
        # Перевірка legal_acts
        if "legal_acts" in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('legal_acts')]
            print("legal_acts:")
            required_columns = ['id', 'nreg', 'title', 'text', 'is_processed', 'embeddings']
            for col in required_columns:
                if col in columns:
                    print(f"   ✅ {col}")
                else:
                    print(f"   ❌ {col} - відсутня!")
        
        # Перевірка categories
        if "categories" in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('categories')]
            print("\ncategories:")
            required_columns = ['id', 'name', 'element_count']
            for col in required_columns:
                if col in columns:
                    print(f"   ✅ {col}")
                else:
                    print(f"   ❌ {col} - відсутня!")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка перевірки структури: {e}")
        return False


def main():
    """Головна функція перевірки"""
    print("\n" + "=" * 80)
    print("ПЕРЕВІРКА НАЛАШТУВАННЯ БАЗИ ДАНИХ")
    print("=" * 80 + "\n")
    
    results = []
    
    # Виконати всі перевірки
    results.append(("Підключення", check_database_connection()))
    results.append(("Таблиці", check_tables()))
    results.append(("pgvector", check_pgvector()))
    results.append(("Дані", check_data()))
    results.append(("Конфігурація", check_config()))
    results.append(("Структура", check_table_structure()))
    
    # Підсумок
    print("\n" + "=" * 80)
    print("ПІДСУМОК")
    print("=" * 80)
    
    all_ok = True
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            all_ok = False
    
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ВСЕ НАЛАШТОВАНО ПРАВИЛЬНО!")
        print("   Можна запускати автоматичне завантаження:")
        print("   python scripts/auto_download_all.py --workers 5")
    else:
        print("⚠️  Є ПРОБЛЕМИ З НАЛАШТУВАННЯМ")
        print("   Виправте помилки перед запуском автоматичного завантаження")
    print("=" * 80 + "\n")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())




