# 🔍 Як перевірити підключення до бази даних

## ✅ Швидка перевірка через API

### 1. Перевірка через статус endpoint

Відкрийте в браузері:
```
https://your-app.railway.app/api/status
```

Або через curl:
```bash
curl https://your-app.railway.app/api/status
```

**Що перевіряти:**
- `database_connected: true` - база підключена
- `database_tables_exist: true` - таблиці створені
- `database_type: "postgresql"` - використовується PostgreSQL (не SQLite)

### 2. Перевірка через логи Railway

1. Відкрийте **Railway Dashboard** → Ваш сервіс → **Deploy Logs**
2. Шукайте повідомлення при старті:
   - ✅ `✔ Using PostgreSQL database (persistent)` - база підключена
   - ⚠️ `⚠️ WARNING: SQLite will lose data on Railway!` - використовується SQLite (не підключено)

### 3. Перевірка змінної DATABASE_URL

1. Відкрийте **Railway Dashboard** → Ваш сервіс → **Variables**
2. Перевірте, чи є змінна `DATABASE_URL`
3. Вона має починатися з `postgresql://`, а не `sqlite://`

**Приклад правильної DATABASE_URL:**
```
postgresql://postgres:password@hostname:5432/railway
```

## 🔧 Якщо база не підключена

### Крок 1: Додати PostgreSQL сервіс

1. В Railway Dashboard натисніть **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway автоматично створить змінну `DATABASE_URL`
3. Перезапустіть сервіс (Railway зробить це автоматично)

### Крок 2: Перевірити підключення

Після перезапуску:
1. Перевірте `/api/status` - має бути `database_connected: true`
2. Перевірте логи - має бути `✔ Using PostgreSQL database`

### Крок 3: Ініціалізувати категорії

Якщо база підключена, але категорій немає:
```bash
POST https://your-app.railway.app/api/legal-acts/initialize-categories
```

## 🚨 Типові проблеми

### Проблема 1: DATABASE_URL не встановлена
**Рішення:** Додайте PostgreSQL сервіс в Railway

### Проблема 2: DATABASE_URL встановлена, але помилка підключення
**Рішення:** 
- Перевірте формат URL
- Перевірте, чи PostgreSQL сервіс запущений
- Перевірте логи на помилки підключення

### Проблема 3: База підключена, але таблиці не створені
**Рішення:** 
- Таблиці створюються автоматично при старті
- Перевірте логи на помилки створення таблиць
- Можна викликати `POST /api/legal-acts/initialize-categories` - він також створює таблиці

## 📝 Додаткова перевірка через Python

Якщо маєте доступ до Railway CLI:

```bash
railway run python -c "
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text

print('DATABASE_URL:', settings.DATABASE_URL[:50] + '...' if settings.DATABASE_URL else 'NOT SET')
print('Database type:', 'PostgreSQL' if settings.DATABASE_URL and 'postgresql' in settings.DATABASE_URL else 'SQLite')

try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version()'))
        print('Connected! PostgreSQL version:', result.fetchone()[0][:50])
except Exception as e:
    print('Connection error:', e)
"
```

