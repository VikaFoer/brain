# Інструкції з перевірки бази даних

## Результати перевірки

Скрипт виявив наступні проблеми:

### ❌ Проблеми:

1. **Файл .env не знайдено**
   - Потрібно створити `.env` файл в корені проекту

2. **Залежності не встановлені**
   - Потрібно встановити Python пакети

## Крок 1: Створення .env файлу

Створіть файл `.env` в корені проекту (`D:\BRAIN\.env`) з наступним вмістом:

```env
# OpenAI
OPENAI_API_KEY=sk-ваш-ключ-тут
OPENAI_MODEL=gpt-5.2-pro
OPENAI_EMBED_MODEL=text-embedding-3-large

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/database_name

# Rada API
RADA_API_BASE_URL=https://data.rada.gov.ua
RADA_API_DELAY=6.0

# Neo4j (опціонально)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ваш-пароль
```

**Важливо:**
- Замініть `user`, `password`, `host`, `database_name` на реальні значення
- Якщо використовуєте Railway, `DATABASE_URL` можна отримати в Railway Dashboard

## Крок 2: Встановлення залежностей

### Варіант A: Встановити всі залежності

```bash
pip install -r requirements.txt
```

### Варіант B: Встановити тільки основні (якщо є проблеми з psycopg2)

```bash
pip install pydantic pydantic-settings sqlalchemy fastapi openai httpx python-dotenv
```

**Примітка:** Якщо на Windows є проблеми з `psycopg2-binary`, можна використати `psycopg` (новий пакет):
```bash
pip install psycopg[binary]
```

## Крок 3: Перевірка підключення до PostgreSQL

### Якщо використовуєте Railway:

1. Відкрийте Railway Dashboard
2. Виберіть ваш PostgreSQL сервіс
3. Перейдіть на вкладку "Variables"
4. Скопіюйте значення `DATABASE_URL`
5. Додайте його в `.env` файл

### Якщо використовуєте локальний PostgreSQL:

```bash
# Перевірка підключення
psql -h localhost -U your_user -d your_database
```

## Крок 4: Повторна перевірка

Після налаштування запустіть:

```bash
# Спрощена перевірка (без повних залежностей)
python scripts/check_database_simple.py

# Повна перевірка (після встановлення залежностей)
python scripts/check_database.py
```

## Крок 5: Створення таблиць (якщо потрібно)

Якщо таблиці ще не створені:

```bash
# Через API (якщо сервер запущений)
curl http://localhost:8000/api/legal-acts/initialize-categories

# Або через Python
python scripts/init_db.py
```

## Перевірка через API

Якщо сервер запущений, можна перевірити через API:

```bash
# Статус системи
curl http://localhost:8000/api/status

# Або відкрити в браузері
http://localhost:8000/api/status
```

Очікуваний результат:
```json
{
  "status": "online",
  "database": {
    "type": "postgresql",
    "connected": true,
    "tables_exist": true,
    "categories_count": 30,
    "legal_acts_count": 0
  }
}
```

## Troubleshooting

### Помилка: "ModuleNotFoundError: No module named 'sqlalchemy'"
**Рішення:** Встановіть залежності: `pip install -r requirements.txt`

### Помилка: "pg_config executable not found"
**Рішення:** 
- Windows: Встановіть PostgreSQL або використайте `psycopg` замість `psycopg2-binary`
- Linux: `sudo apt-get install libpq-dev`

### Помилка: "DATABASE_URL not set"
**Рішення:** Створіть `.env` файл з правильним `DATABASE_URL`

### Помилка: "Connection refused"
**Рішення:** 
- Перевірте, чи запущений PostgreSQL
- Перевірте правильність `DATABASE_URL`
- Перевірте firewall/мережеві налаштування

## Після успішної перевірки

Коли всі перевірки пройдуть успішно, можна запускати автоматичне завантаження:

```bash
python scripts/auto_download_all.py --workers 5
```

