"""
Простий скрипт для перевірки OpenAI API конфігурації (без W&B)
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Спочатку перевіримо чи є ключ, перш ніж імпортувати сервіси
from app.core.config import settings

print("=" * 60)
print("Перевірка конфігурації OpenAI API")
print("=" * 60)

# 1. Check API key
print("\n1. API Key:")
if settings.OPENAI_API_KEY:
    key_preview = settings.OPENAI_API_KEY[:10] + "..." + settings.OPENAI_API_KEY[-4:]
    print(f"   [OK] API ключ налаштований: {key_preview}")
    has_key = True
else:
    print("   [ERROR] API ключ НЕ налаштований!")
    print("   Додайте OPENAI_API_KEY до .env файлу або змінних середовища")
    has_key = False

# 2. Check model
print(f"\n2. Модель: {settings.OPENAI_MODEL}")

# 3. Simple import test
print("\n3. Перевірка імпортів:")
try:
    from openai import AsyncOpenAI
    print("   [OK] openai модуль встановлено")
    
    if has_key:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        print("   [OK] OpenAI client можна створити")
    else:
        print("   [WARN] Не можу створити client без API ключа")
        
except ImportError as e:
    print(f"   [ERROR] Помилка імпорту openai: {e}")
    print("   Встановіть: pip install openai")

# 4. Check OpenAI service
print("\n4. OpenAI Service:")
try:
    from app.services.openai_service import openai_service
    
    if openai_service.client:
        print("   [OK] OpenAI service ініціалізовано")
        print(f"   [OK] Модель: {openai_service.model}")
    else:
        print("   [ERROR] OpenAI service НЕ ініціалізовано")
        print("   Причина: OPENAI_API_KEY не налаштований")
        
except Exception as e:
    print(f"   [WARN] Помилка при перевірці service: {e}")

print("\n" + "=" * 60)
if has_key:
    print("[OK] API ключ налаштований")
    print("\nНаступні кроки:")
    print("1. Перевірте логи на Railway для деталей")
    print("2. Спробуйте обробити акт через API:")
    print("   POST /api/legal-acts/{nreg}/process")
    print("3. Перевірте використання на platform.openai.com/usage")
else:
    print("[ERROR] ПРОБЛЕМА: API ключ не налаштований!")
    print("\nРішення:")
    print("1. Railway -> Settings -> Variables")
    print("2. Додайте OPENAI_API_KEY=sk-...")
    print("3. Перезапустіть сервіс")
print("=" * 60)

