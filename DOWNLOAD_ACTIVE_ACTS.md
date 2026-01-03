# Інструкція з завантаження діючих НПА

## Огляд

Створено рішення для завантаження **тільки діючих** нормативно-правових актів з Rada API в базу даних.

## Що вважається "діючим" актом?

Діючі статуси:
- "діє"
- "діючий"
- "в дії"
- "чинний"
- "active"
- "valid"
- "в силі"
- `None` (якщо статус не вказано, вважаємо діючим)

Недіючі статуси (пропускаються):
- "втратив чинність"
- "скасовано"
- "недійсний"
- "застарілий"

## Спосіб 1: Через API (рекомендовано)

### Завантажити тільки діючі НПА (без обробки)

```bash
curl -X POST "http://localhost:8000/api/legal-acts/download-active-acts"
```

### Завантажити та обробити діючі НПА

```bash
curl -X POST "http://localhost:8000/api/legal-acts/download-active-acts?process=true"
```

### Через браузер

Відкрийте адмін панель або використайте:
```
POST /api/legal-acts/download-active-acts?process=true
```

## Спосіб 2: Через скрипт

### Базове використання

```bash
python scripts/download_active_acts.py
```

### З параметрами

```bash
# З 10 паралельними воркерами
python scripts/download_active_acts.py --workers 10

# Завантажити всі (без фільтрації за статусом)
python scripts/download_active_acts.py --no-filter

# Не пропускати вже оброблені
python scripts/download_active_acts.py --no-resume

# Обмежити кількість для тестування
python scripts/download_active_acts.py --limit 100
```

## Як це працює

1. **Отримання списку НПА:**
   - Спочатку намагається отримати через open data portal API
   - Якщо не працює, використовує стандартний метод (HTML парсинг)

2. **Фільтрація діючих:**
   - Для кожного NREG отримує картку документа
   - Перевіряє статус акту
   - Пропускає недіючі акти

3. **Завантаження в базу:**
   - Створює записи в базі даних з мінімальною інформацією
   - Оновлює існуючі записи якщо потрібно

4. **Обробка (опціонально):**
   - Якщо `process=true`, обробляє через OpenAI
   - Виділяє елементи множини та зв'язки

## Статистика

Після завершення ви побачите:
- Всього документів знайдено
- Діючих документів
- Недіючих (пропущено)
- Створено нових записів
- Оновлено існуючих
- Оброблено через OpenAI (якщо `process=true`)

## Логи

Всі операції логуються:
- В консоль (для скрипта)
- В файл `download_active_acts.log` (для скрипта)
- В Railway logs (для API)

## Приклади використання

### Завантажити діючі НПА через API

```python
import requests

# Тільки завантажити
response = requests.post("http://localhost:8000/api/legal-acts/download-active-acts")
print(response.json())

# Завантажити та обробити
response = requests.post(
    "http://localhost:8000/api/legal-acts/download-active-acts",
    params={"process": True}
)
print(response.json())
```

### Запустити скрипт локально

```bash
# Встановити залежності (якщо потрібно)
pip install -r requirements.txt

# Запустити
python scripts/download_active_acts.py --workers 5
```

## Налаштування

### Кількість паралельних воркерів

Збільште для швидшої обробки (але врахуйте rate limits Rada API):

```bash
python scripts/download_active_acts.py --workers 10
```

### Rate limiting

Rada API має обмеження на кількість запитів. Налаштування в `.env`:

```env
RADA_API_DELAY=6.0  # секунд між запитами
RADA_API_RATE_LIMIT=60  # запитів на хвилину
```

## Troubleshooting

### Помилка: "No documents found from Rada API"

**Рішення:**
1. Перевірте доступність `https://data.rada.gov.ua`
2. Спробуйте вказати `RADA_OPEN_DATA_DATASET_ID` в `.env`
3. Перевірте логи для деталей

### Занадто повільно

**Рішення:**
1. Збільште `--workers` (але не більше 10-15)
2. Переконайтеся, що `RADA_API_DELAY` не занадто великий
3. Використайте open data API (швидше ніж HTML парсинг)

### Багато недіючих актів пропущено

Це нормально! Система фільтрує тільки діючі акти. Якщо потрібні всі:

```bash
python scripts/download_active_acts.py --no-filter
```

## Порівняння методів

| Метод | Швидкість | Надійність | Фільтрація |
|-------|-----------|------------|-------------|
| Open Data API | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |
| HTML парсинг | ⭐⭐⭐ | ⭐⭐⭐ | ✅ |
| Скрипт | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| API endpoint | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |

## Наступні кроки

Після завантаження діючих НПА:

1. **Перевірте статистику:**
   ```bash
   curl http://localhost:8000/api/status
   ```

2. **Обробіть через OpenAI** (якщо ще не оброблено):
   ```bash
   curl -X POST "http://localhost:8000/api/legal-acts/process-all-overnight"
   ```

3. **Перевірте в адмін панелі:**
   Відкрийте `/admin` та перегляньте завантажені акти

