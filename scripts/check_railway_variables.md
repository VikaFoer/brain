# Діагностика проблеми з DATABASE_URL на Railway

## Що перевірити

### 1. Перевірте, чи сервіс перезапустився

Railway Dashboard → сервіс "brain" → Deployments

Має бути останній деплой після додавання змінної. Якщо ні - натисніть "Redeploy".

### 2. Перевірте змінну в Railway

Railway Dashboard → сервіс "brain" → Variables

Має бути:
- **Name:** `DATABASE_URL` (точно так, великі літери, підкреслення)
- **Value:** або `${{Postgres.DATABASE_URL}}` (Reference) або `postgresql://...` (пряме значення)

### 3. Перевірте через debug endpoint

Після деплою відкрийте:
```
https://brain-production-1712.up.railway.app/api/debug/env
```

Це покаже, що саме бачить додаток.

### 4. Перевірте логи Railway

Railway Dashboard → сервіс "brain" → Deploy Logs

Шукайте:
- `✔ Using PostgreSQL database` - правильно
- `⚠️ WARNING: SQLite` - неправильно, DATABASE_URL не працює

### 5. Якщо Reference не працює - скопіюйте вручну

1. Railway Dashboard → сервіс "Postgres" → Variables
2. Знайдіть `DATABASE_URL`
3. Натисніть на значення → скопіюйте (виглядає як `postgresql://postgres:xxx@xxx:5432/railway`)
4. Railway Dashboard → сервіс "brain" → Variables
5. Видаліть поточний `DATABASE_URL` (якщо є)
6. "+ New Variable"
7. Name: `DATABASE_URL`
8. Value: вставте скопійоване значення
9. "Add"
10. Дочекайтеся автоматичного перезапуску (1-2 хвилини)

### 6. Вручну перезапустити сервіс

Якщо після додавання змінної сервіс не перезапустився:

Railway Dashboard → сервіс "brain" → Settings → "Redeploy"

## Типові помилки

### Помилка: "DATABASE-URL" замість "DATABASE_URL"
- ❌ Неправильно: `DATABASE-URL` (з тире)
- ✅ Правильно: `DATABASE_URL` (з підкресленням)

### Помилка: "database_url" замість "DATABASE_URL"
- ❌ Неправильно: `database_url` (малі літери)
- ✅ Правильно: `DATABASE_URL` (великі літери)

### Помилка: Reference не розкривається
- Якщо `${{Postgres.DATABASE_URL}}` не працює - скопіюйте значення вручну

## Після виправлення

Оновіть сторінку:
```
https://brain-production-1712.up.railway.app/api/status
```

Має показати:
- `type: "postgresql"`
- `connected: true`
- `url_set: true`

