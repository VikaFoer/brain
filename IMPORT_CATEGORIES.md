# Інструкція з імпорту категорій нормативно-правових актів

## Що було додано

1. **Поле `code` в моделі Category** - для зберігання номера класифікації
2. **API endpoint `/api/legal-acts/import-categories`** - для імпорту категорій через API
3. **Скрипт `scripts/import_categories.py`** - для імпорту з текстового файлу

## Спосіб 1: Імпорт через API (рекомендовано)

### Формат даних

Потрібно відправити POST запит на `/api/legal-acts/import-categories` з JSON у форматі:

```json
[
  {"code": 1, "name": "Основи суспільного ладу"},
  {"code": 2, "name": "Конституція"},
  {"code": 3, "name": "Прийняття"},
  ...
]
```

### Приклад використання через curl

```bash
curl -X POST "http://localhost:8000/api/legal-acts/import-categories" \
  -H "Content-Type: application/json" \
  -d @categories.json
```

### Приклад через Python

```python
import requests

categories = [
    {"code": 1, "name": "Основи суспільного ладу"},
    {"code": 2, "name": "Конституція"},
    # ... додайте всі категорії
]

response = requests.post(
    "http://localhost:8000/api/legal-acts/import-categories",
    json=categories
)
print(response.json())
```

## Спосіб 2: Імпорт через скрипт

### Формат файлу

Створіть файл `categories.txt` у форматі:
```
1	Основи суспільного ладу
2	Конституція
3	Прийняття
...
```

### Виконання скрипту

```bash
# З файлу
python scripts/import_categories.py categories.txt

# Або через stdin (вставте текст і натисніть Ctrl+D / Ctrl+Z)
python scripts/import_categories.py
```

## Створення JSON файлу з ваших даних

Якщо у вас є список у форматі "номер\tназва", ви можете конвертувати його в JSON:

```python
# convert_categories.py
import json

text = """1	Основи суспільного ладу
2	Конституція
3	Прийняття
..."""

categories = []
for line in text.strip().split('\n'):
    parts = line.split('\t', 1)
    if len(parts) == 2:
        categories.append({
            "code": int(parts[0].strip()),
            "name": parts[1].strip()
        })

with open('categories.json', 'w', encoding='utf-8') as f:
    json.dump(categories, f, ensure_ascii=False, indent=2)

print(f"Created categories.json with {len(categories)} categories")
```

## Перевірка результатів

Після імпорту перевірте кількість категорій:

```bash
# Через API
curl http://localhost:8000/api/categories/

# Або через адмін панель
# Відкрийте http://localhost:8000/admin
```

## Примітки

- Якщо категорія з такою назвою вже існує, вона буде оновлена (код буде змінено, якщо вказано)
- Нові категорії будуть створені з `element_count=0`
- Код категорії (поле `code`) є опціональним

