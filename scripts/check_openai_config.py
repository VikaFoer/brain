"""
Script to check OpenAI API configuration and test API calls
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.openai_service import openai_service
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_openai_config():
    """Check OpenAI configuration and test API call"""
    
    print("=" * 60)
    print("Перевірка конфігурації OpenAI API")
    print("=" * 60)
    
    # 1. Check API key
    print("\n1. API Key:")
    if settings.OPENAI_API_KEY:
        key_preview = settings.OPENAI_API_KEY[:10] + "..." + settings.OPENAI_API_KEY[-4:]
        print(f"   ✅ API ключ налаштований: {key_preview}")
    else:
        print("   ❌ API ключ НЕ налаштований!")
        print("   Додайте OPENAI_API_KEY до .env файлу або змінних середовища")
        return False
    
    # 2. Check model
    print(f"\n2. Модель: {settings.OPENAI_MODEL}")
    
    # 3. Check OpenAI service
    print("\n3. OpenAI Service:")
    if openai_service.client:
        print("   ✅ OpenAI client ініціалізовано")
    else:
        print("   ❌ OpenAI client НЕ ініціалізовано")
        return False
    
    # 4. Test API call
    print("\n4. Тестовий виклик API:")
    try:
        # Simple test call
        response = await openai_service.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "user", "content": "Скажи 'OK' українською"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"   ✅ API працює! Відповідь: {result}")
        print("   💰 Цей виклик коштував приблизно $0.001")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Помилка API виклику: {e}")
        print(f"   Тип помилки: {type(e).__name__}")
        return False


async def check_extraction():
    """Check if extraction works"""
    print("\n" + "=" * 60)
    print("Перевірка extract_set_elements")
    print("=" * 60)
    
    test_text = "Стаття 1. Цей Закон регулює правові відносини."
    test_title = "Тестовий закон"
    
    try:
        result = await openai_service.extract_set_elements(
            legal_act_text=test_text,
            act_title=test_title,
            categories=[]
        )
        
        if result and (result.get("categories") or result.get("elements")):
            print("   ✅ extract_set_elements працює!")
            print(f"   Знайдено: {len(result.get('elements', []))} елементів")
            print("   💰 Цей виклик коштував приблизно $0.01-0.05")
            return True
        else:
            print("   ⚠️  extract_set_elements повернув порожній результат")
            print("   Можливо, тестовий текст занадто короткий")
            return False
            
    except Exception as e:
        print(f"   ❌ Помилка extract_set_elements: {e}")
        return False


async def main():
    """Main function"""
    print("\n🔍 Діагностика OpenAI API конфігурації\n")
    
    # Check config
    config_ok = await check_openai_config()
    
    if config_ok:
        # Test extraction
        extraction_ok = await check_extraction()
        
        print("\n" + "=" * 60)
        if config_ok and extraction_ok:
            print("✅ Все працює правильно!")
            print("Якщо закони не обробляються, перевірте:")
            print("1. Чи викликається process_legal_act()")
            print("2. Чи є тексти у legal acts")
            print("3. Перевірте логи на Railway")
        else:
            print("⚠️  Є проблеми з конфігурацією")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Проблема з конфігурацією OpenAI API")
        print("Перевірте OPENAI_API_KEY у змінних середовища")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

