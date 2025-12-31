#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Перевірка налаштування бази даних на Railway
"""
import os
import sys
from pathlib import Path
import requests
import json

# Налаштування кодування для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_railway_status(railway_url: str = None):
    """Перевірка статусу через Railway API endpoint"""
    print("=" * 80)
    print("ПЕРЕВІРКА БАЗИ ДАНИХ НА RAILWAY")
    print("=" * 80)
    
    # Отримати Railway URL
    if not railway_url:
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if not railway_url:
            print("⚠️  RAILWAY_PUBLIC_DOMAIN не встановлено")
            print("   Вкажіть URL вашого Railway сервісу:")
            print("   python scripts/check_database_railway.py https://your-app.railway.app")
            return False
    
    # Додати https якщо потрібно
    if not railway_url.startswith('http'):
        railway_url = f"https://{railway_url}"
    
    status_url = f"{railway_url}/api/status"
    
    print(f"\nПеревірка статусу через: {status_url}")
    print("-" * 80)
    
    try:
        response = requests.get(status_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Помилка: HTTP {response.status_code}")
            print(f"   Відповідь: {response.text[:200]}")
            return False
        
        data = response.json()
        
        # Вивести статус
        print(f"\n✅ Статус системи: {data.get('status', 'unknown')}")
        
        # База даних
        db_info = data.get('database', {})
        print(f"\n📊 База даних:")
        print(f"   Тип: {db_info.get('type', 'unknown')}")
        print(f"   Підключено: {'✅' if db_info.get('connected') else '❌'}")
        print(f"   Таблиці існують: {'✅' if db_info.get('tables_exist') else '❌'}")
        print(f"   Категорій: {db_info.get('categories_count', 0)}")
        print(f"   Документів: {db_info.get('legal_acts_count', 0)}")
        print(f"   Ініціалізовано: {'✅' if db_info.get('initialized') else '❌'}")
        
        if db_info.get('url_preview'):
            print(f"   URL: {db_info.get('url_preview')}")
        
        if db_info.get('error'):
            print(f"   ⚠️  Помилка: {db_info.get('error')}")
        
        # OpenAI
        openai_info = data.get('openai', {})
        print(f"\n🤖 OpenAI:")
        print(f"   Налаштовано: {'✅' if openai_info.get('configured') else '❌'}")
        print(f"   Модель: {openai_info.get('model', 'N/A')}")
        
        # Neo4j
        neo4j_info = data.get('neo4j', {})
        print(f"\n🕸️  Neo4j:")
        print(f"   Налаштовано: {'✅' if neo4j_info.get('configured') else '❌'}")
        print(f"   Статус: {neo4j_info.get('status', 'unknown')}")
        
        # Rada API
        rada_info = data.get('rada_api', {})
        print(f"\n📡 Rada API:")
        print(f"   Налаштовано: {'✅' if rada_info.get('configured') else '⚠️'}")
        print(f"   Base URL: {rada_info.get('base_url', 'N/A')}")
        
        # Підсумок
        print("\n" + "=" * 80)
        print("ПІДСУМОК")
        print("=" * 80)
        
        all_ok = (
            db_info.get('connected') and
            db_info.get('tables_exist') and
            openai_info.get('configured')
        )
        
        if all_ok:
            print("✅ ВСЕ НАЛАШТОВАНО ПРАВИЛЬНО!")
            print("\nМожна запускати автоматичне завантаження:")
            print("   python scripts/auto_download_all.py --workers 5")
        else:
            print("⚠️  Є ПРОБЛЕМИ:")
            if not db_info.get('connected'):
                print("   ❌ База даних не підключена")
                print("      Перевірте Railway Dashboard → Variables → DATABASE_URL")
            if not db_info.get('tables_exist'):
                print("   ❌ Таблиці не створені")
                print("      Відкрийте: https://your-app.railway.app/api/legal-acts/initialize-categories")
            if not openai_info.get('configured'):
                print("   ❌ OpenAI API key не налаштовано")
                print("      Додайте OPENAI_API_KEY в Railway Dashboard → Variables")
        
        print("=" * 80)
        
        return all_ok
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Не вдалося підключитися до {status_url}")
        print("   Перевірте:")
        print("   1. Чи запущений сервіс на Railway")
        print("   2. Чи правильний URL")
        print("   3. Чи немає проблем з мережею")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут підключення до {status_url}")
        return False
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False


def check_local_env():
    """Перевірка локальних змінних середовища"""
    print("\n" + "=" * 80)
    print("ПЕРЕВІРКА ЛОКАЛЬНИХ ЗМІННИХ")
    print("=" * 80)
    
    railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    database_url = os.getenv('DATABASE_URL')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"\nRailway URL: {'✅' if railway_url else '❌'} {railway_url or 'не встановлено'}")
    print(f"Database URL: {'✅' if database_url else '❌'} {'встановлено' if database_url else 'не встановлено'}")
    print(f"OpenAI Key: {'✅' if openai_key else '❌'} {'встановлено' if openai_key else 'не встановлено'}")
    
    if railway_url:
        print(f"\n💡 Використайте URL: https://{railway_url}")
    elif database_url and 'railway.app' in database_url:
        # Спробувати витягти URL з DATABASE_URL
        print(f"\n💡 Знайдено Railway DATABASE_URL")
        print(f"   Перевірте Railway Dashboard для Public Domain")
    
    return railway_url or database_url


def main():
    """Головна функція"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Перевірка бази даних на Railway")
    parser.add_argument(
        "url",
        nargs="?",
        help="URL Railway сервісу (наприклад: https://your-app.railway.app)"
    )
    
    args = parser.parse_args()
    
    railway_url = args.url
    
    # Якщо URL не вказано, спробувати знайти
    if not railway_url:
        railway_url = check_local_env()
    
    if not railway_url:
        print("\n" + "=" * 80)
        print("⚠️  Railway URL не знайдено")
        print("=" * 80)
        print("\nВкажіть URL вашого Railway сервісу:")
        print("   python scripts/check_database_railway.py https://your-app.railway.app")
        print("\nАбо встановіть змінну середовища:")
        print("   set RAILWAY_PUBLIC_DOMAIN=your-app.railway.app")
        print("=" * 80)
        return 1
    
    # Перевірити статус
    success = check_railway_status(railway_url)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПерервано користувачем")
        sys.exit(1)

