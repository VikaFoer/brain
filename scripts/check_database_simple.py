#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Спрощена перевірка налаштування бази даних (без повних залежностей)
"""
import os
import sys
from pathlib import Path

# Налаштування кодування для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Додати шлях до проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env_file():
    """Перевірка .env файлу"""
    print("=" * 80)
    print("1. ПЕРЕВІРКА .env ФАЙЛУ")
    print("=" * 80)
    
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("❌ .env файл не знайдено!")
        print(f"   Шлях: {env_path}")
        print("   Створіть .env файл з наступними змінними:")
        print("   - DATABASE_URL=postgresql://...")
        print("   - OPENAI_API_KEY=sk-...")
        return False
    
    print(f"✅ .env файл знайдено: {env_path}")
    
    # Читаємо .env
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # Перевірка ключових змінних
    required = ['DATABASE_URL', 'OPENAI_API_KEY']
    all_ok = True
    
    for var in required:
        if var in env_vars and env_vars[var]:
            # Приховати значення
            value = env_vars[var]
            if 'password' in var.lower() or 'key' in var.lower():
                if len(value) > 10:
                    display_value = value[:4] + "..." + value[-4:]
                else:
                    display_value = "***"
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"   ✅ {var} = {display_value}")
        else:
            print(f"   ❌ {var} - не встановлено")
            all_ok = False
    
    # Опціональні змінні
    optional = ['RADA_API_TOKEN', 'NEO4J_PASSWORD', 'NEO4J_URI']
    print(f"\nОпціональні змінні:")
    for var in optional:
        if var in env_vars and env_vars[var]:
            print(f"   ✅ {var} = встановлено")
        else:
            print(f"   ⚠️  {var} - не встановлено (опціонально)")
    
    return all_ok


def check_database_url():
    """Перевірка формату DATABASE_URL"""
    print("\n" + "=" * 80)
    print("2. ПЕРЕВІРКА DATABASE_URL")
    print("=" * 80)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print("❌ DATABASE_URL не встановлено")
            return False
        
        if db_url.startswith('sqlite'):
            print("⚠️  ВИКОРИСТОВУЄТЬСЯ SQLite!")
            print("   SQLite не підходить для production")
            print("   Рекомендовано: PostgreSQL")
            return False
        elif db_url.startswith('postgresql'):
            print("✅ Використовується PostgreSQL")
            
            # Перевірка формату
            if '@' in db_url and '://' in db_url:
                print("   ✅ Формат URL правильний")
                return True
            else:
                print("   ⚠️  Формат URL може бути неправильним")
                return False
        else:
            print(f"⚠️  Невідомий тип бази даних: {db_url[:20]}...")
            return False
            
    except ImportError:
        print("⚠️  python-dotenv не встановлено, не можу перевірити .env")
        return None
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False


def check_dependencies():
    """Перевірка встановлених залежностей"""
    print("\n" + "=" * 80)
    print("3. ПЕРЕВІРКА ЗАЛЕЖНОСТЕЙ")
    print("=" * 80)
    
    required = {
        'pydantic': 'pydantic',
        'pydantic_settings': 'pydantic-settings',
        'sqlalchemy': 'sqlalchemy',
        'fastapi': 'fastapi',
        'openai': 'openai',
    }
    
    optional = {
        'psycopg': 'psycopg2-binary або psycopg',
        'neo4j': 'neo4j',
    }
    
    all_ok = True
    
    print("Обов'язкові:")
    for module, package in required.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - не встановлено")
            all_ok = False
    
    print("\nОпціональні:")
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ⚠️  {package} - не встановлено (опціонально)")
    
    return all_ok


def check_database_connection_simple():
    """Спрощена перевірка підключення (якщо можливо)"""
    print("\n" + "=" * 80)
    print("4. ПЕРЕВІРКА ПІДКЛЮЧЕННЯ ДО БАЗИ ДАНИХ")
    print("=" * 80)
    
    try:
        from app.core.config import settings
        from app.core.database import engine
        from sqlalchemy import text
        
        if not settings.DATABASE_URL:
            print("❌ DATABASE_URL не встановлено")
            return False
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            print("✅ Підключення до бази даних успішне")
            
            # Перевірка таблиць
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            required_tables = ['categories', 'legal_acts']
            print(f"\nЗнайдено таблиць: {len(tables)}")
            
            for table in required_tables:
                if table in tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} - відсутня")
            
            return True
            
        except Exception as e:
            print(f"❌ Помилка підключення: {e}")
            return False
            
    except ImportError as e:
        print(f"⚠️  Не можу перевірити (відсутні залежності): {e}")
        print("   Встановіть залежності: pip install -r requirements.txt")
        return None
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False


def main():
    """Головна функція"""
    print("\n" + "=" * 80)
    print("ПЕРЕВІРКА НАЛАШТУВАННЯ БАЗИ ДАНИХ (СПРОЩЕНА ВЕРСІЯ)")
    print("=" * 80 + "\n")
    
    results = []
    
    # Перевірки
    results.append(("Файл .env", check_env_file()))
    results.append(("DATABASE_URL", check_database_url()))
    results.append(("Залежності", check_dependencies()))
    
    # Спроба перевірити підключення (якщо залежності встановлені)
    conn_result = check_database_connection_simple()
    if conn_result is not None:
        results.append(("Підключення", conn_result))
    
    # Підсумок
    print("\n" + "=" * 80)
    print("ПІДСУМОК")
    print("=" * 80)
    
    all_ok = True
    for name, result in results:
        if result is None:
            status = "⚠️"
        elif result:
            status = "✅"
        else:
            status = "❌"
            all_ok = False
        print(f"{status} {name}")
    
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ ОСНОВНІ ПЕРЕВІРКИ ПРОЙДЕНО")
        print("\nДля повної перевірки встановіть залежності:")
        print("   pip install -r requirements.txt")
        print("\nПотім запустіть:")
        print("   python scripts/check_database.py")
    else:
        print("⚠️  Є ПРОБЛЕМИ")
        print("   Виправте помилки перед продовженням")
    print("=" * 80 + "\n")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

