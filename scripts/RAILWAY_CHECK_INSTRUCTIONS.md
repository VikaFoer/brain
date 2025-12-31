# Перевірка бази даних на Railway

## Швидка перевірка через браузер

1. Відкрийте ваш Railway сервіс в браузері:
   ```
   https://your-app.railway.app/api/status
   ```

2. Перевірте відповідь - має бути JSON з інформацією про базу даних

## Перевірка через скрипт

### Варіант 1: Вказати URL вручну

```bash
python scripts/check_database_railway.py https://your-app.railway.app
```

### Варіант 2: Використати змінну середовища

```bash
# Windows PowerShell
$env:RAILWAY_PUBLIC_DOMAIN="your-app.railway.app"
python scripts/check_database_railway.py

# Linux/Mac
export RAILWAY_PUBLIC_DOMAIN="your-app.railway.app"
python scripts/check_database_railway.py
```

## Що перевіряє скрипт

✅ **Підключення до бази даних**
- Тип бази (PostgreSQL/SQLite)
- Статус підключення
- Наявність таблиць

✅ **Дані**
- Кількість категорій
- Кількість документів
- Статус ініціалізації

✅ **Налаштування**
- OpenAI API key
- Neo4j (опціонально)
- Rada API

## Як знайти Railway URL

1. Відкрийте [Railway Dashboard](https://railway.app)
2. Виберіть ваш проект
3. Виберіть сервіс з додатком (не PostgreSQL!)
4. Перейдіть на вкладку **"Settings"**
5. Знайдіть **"Public Domain"** або **"Custom Domain"**
6. Скопіюйте URL (наприклад: `brain-production-1712.up.railway.app`)

## Типові проблеми та рішення

### ❌ "База даних не підключена"

**Проблема:** `DATABASE_URL` не підключений до сервісу з додатком

**Рішення:**
1. Railway Dashboard → Ваш проект
2. Виберіть сервіс з додатком (не PostgreSQL!)
3. Settings → Variables
4. Натисніть "+ New Variable"
5. Name: `DATABASE_URL`
6. Value: натисніть 🔗 (Reference)
7. Service: виберіть ваш PostgreSQL сервіс
8. Variable: `DATABASE_URL`
9. Натисніть "Add"

Railway автоматично перезапустить сервіс.

### ❌ "Таблиці не створені"

**Рішення:**
Відкрийте в браузері:
```
https://your-app.railway.app/api/legal-acts/initialize-categories
```

Або через curl:
```bash
curl https://your-app.railway.app/api/legal-acts/initialize-categories
```

### ❌ "OpenAI API key не налаштовано"

**Рішення:**
1. Railway Dashboard → Ваш сервіс
2. Settings → Variables
3. "+ New Variable"
4. Name: `OPENAI_API_KEY`
5. Value: `sk-ваш-ключ`
6. "Add"

### ❌ "Не вдалося підключитися"

**Можливі причини:**
- Сервіс не запущений (перевірте Railway Dashboard)
- Неправильний URL
- Проблеми з мережею

**Рішення:**
1. Перевірте Railway Dashboard → чи сервіс "Online"
2. Перевірте логи: Railway Dashboard → Deploy Logs
3. Перевірте правильність URL

## Перевірка через Railway Dashboard

### 1. Перевірка змінних середовища

Railway Dashboard → Ваш сервіс → Settings → Variables

Мають бути:
- ✅ `DATABASE_URL` (Reference до PostgreSQL)
- ✅ `OPENAI_API_KEY`
- ⚠️ `RADA_API_TOKEN` (опціонально)
- ⚠️ `NEO4J_PASSWORD` (опціонально)

### 2. Перевірка логів

Railway Dashboard → Ваш сервіс → Deploy Logs

Шукайте:
- ✅ `✔ Using PostgreSQL database (persistent)`
- ❌ `⚠️ WARNING: SQLite will lose data` (неправильно!)

### 3. Перевірка підключення до PostgreSQL

Railway Dashboard → PostgreSQL сервіс → Connect

Можна підключитися через psql або pgAdmin.

## Після успішної перевірки

Коли всі перевірки пройдуть успішно:

```bash
# Запустити автоматичне завантаження
python scripts/auto_download_all.py --workers 5
```

## Моніторинг прогресу

Перевірити скільки документів оброблено:

```bash
# Через API
curl https://your-app.railway.app/api/status | jq .database.legal_acts_count

# Або відкрити в браузері
https://your-app.railway.app/api/status
```

## Додаткова інформація

- [Railway Database Setup](../RAILWAY_DATABASE.md)
- [Connect PostgreSQL to App](../CONNECT_POSTGRES_TO_APP.md)
- [Check Database](../CHECK_DATABASE.md)

