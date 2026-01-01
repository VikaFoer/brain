# Діагностика проблеми: закони не обробляються

## Проблема
Користувач повідомляє, що закони не обробляються і не тратяться кошти з OpenAI API.

## Можливі причини

### 1. OpenAI API ключ не налаштований
**Симптоми:**
- В логах: "OpenAI API key is not configured"
- extract_set_elements повертає порожній результат без виклику API
- Кошти не тратяться

**Рішення:**
Перевірте змінні середовища на Railway:
- `OPENAI_API_KEY` має бути встановлений

**Перевірка:**
```bash
python scripts/check_openai_config.py
```

### 2. Помилка з embeddings блокує обробку
**Симптоми:**
- В логах: "Error generating embeddings: AsyncEmbeddings.create() got an unexpected keyword argument 'dimensions'"
- Embeddings не генеруються
- Але це НЕ повинно блокувати extract_set_elements

**Рішення:**
Embeddings генеруються після extract_set_elements, тому це не має блокувати обробку.
Але можна виправити помилку для кращої роботи.

### 3. extract_set_elements не викликається
**Симптоми:**
- Немає логів "Extracting elements from {nreg} using OpenAI..."
- Кошти не тратяться

**Можливі причини:**
- `process_legal_act()` не викликається
- Акти вже позначені як оброблені (`is_processed=True`)
- Немає тексту у legal acts (`text` is None)

**Перевірка:**
```python
# Перевірити скільки актів потребують обробки
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct

db = SessionLocal()
unprocessed = db.query(LegalAct).filter(
    LegalAct.is_processed == False,
    LegalAct.text.isnot(None)
).count()
print(f"Актів потребують обробки: {unprocessed}")
```

### 4. extract_set_elements повертає порожній результат
**Симптоми:**
- В логах: "Extraction returned empty result"
- Виклик API відбувається, але результат порожній
- Кошти можуть трохи тратитися (неуспішні виклики)

**Можливі причини:**
- JSON parsing error (обрізана відповідь)
- Модель повертає порожній результат
- Помилки в prompt або форматі

## Діагностичні кроки

### Крок 1: Перевірка конфігурації
```bash
python scripts/check_openai_config.py
```

Це покаже:
- Чи налаштований API ключ
- Чи працює API
- Чи працює extract_set_elements

### Крок 2: Перевірка бази даних
```python
# Перевірити акти
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct

db = SessionLocal()

# Всього актів
total = db.query(LegalAct).count()
print(f"Всього актів: {total}")

# Оброблених
processed = db.query(LegalAct).filter(LegalAct.is_processed == True).count()
print(f"Оброблених: {processed}")

# Потребують обробки
unprocessed = db.query(LegalAct).filter(
    LegalAct.is_processed == False,
    LegalAct.text.isnot(None)
).count()
print(f"Потребують обробки: {unprocessed}")

# Без тексту
no_text = db.query(LegalAct).filter(LegalAct.text == None).count()
print(f"Без тексту: {no_text}")
```

### Крок 3: Перевірка логів на Railway
Перевірте логи на Railway для:
1. "Extracting elements from {nreg} using OpenAI..."
2. "OpenAI API key is not configured"
3. "Failed to parse OpenAI response as JSON"
4. "Extraction returned empty result"

### Крок 4: Тестовий запуск обробки
```python
# Обробити один акт вручну
from app.core.database import SessionLocal
from app.services.processing_service import ProcessingService
import asyncio

async def test_processing():
    db = SessionLocal()
    service = ProcessingService(db)
    
    # Знайти необроблений акт
    act = db.query(LegalAct).filter(
        LegalAct.is_processed == False,
        LegalAct.text.isnot(None)
    ).first()
    
    if act:
        print(f"Обробляю акт: {act.nreg}")
        result = await service.process_legal_act(act.nreg)
        if result and result.is_processed:
            print("✅ Успішно оброблено!")
        else:
            print("❌ Не вдалося обробити")
    else:
        print("Немає актів для обробки")

asyncio.run(test_processing())
```

## Швидке виправлення

### Якщо API ключ не налаштований:
1. Перейдіть на Railway → Settings → Variables
2. Додайте `OPENAI_API_KEY` з вашим ключем
3. Перезапустіть сервіс

### Якщо акти вже позначені як оброблені:
```python
# Скинути статус обробки для тестування
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct

db = SessionLocal()
db.query(LegalAct).update({LegalAct.is_processed: False})
db.commit()
print("Статус обробки скинуто")
```

### Якщо немає текстів:
Перевірте чи акти завантажуються з Rada API правильно.

## Очікувана поведінка

Коли все працює правильно:
1. ✅ В логах: "Extracting elements from {nreg} using OpenAI..."
2. ✅ В логах: "Successfully extracted {count} elements"
3. ✅ Кошти тратяться (перевірте на platform.openai.com)
4. ✅ `is_processed=True` в базі даних
5. ✅ `extracted_elements` заповнений JSON

## Контрольний список

- [ ] `OPENAI_API_KEY` встановлений на Railway
- [ ] API працює (перевірено через check_openai_config.py)
- [ ] Є акти з `is_processed=False` та `text IS NOT NULL`
- [ ] В логах є повідомлення "Extracting elements..."
- [ ] Немає помилок "API key is not configured"
- [ ] Кошти тратяться на platform.openai.com

