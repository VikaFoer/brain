# Railway Deployment Guide

## Налаштування змінних оточення

В Railway Dashboard → Variables додайте:

### Обов'язкові:
- `OPENAI_API_KEY` - ваш ключ OpenAI
- `SECRET_KEY` - випадковий рядок для безпеки

### Опціональні (для повної функціональності):
- `DATABASE_URL` - URL PostgreSQL (Railway може надати автоматично)
- `NEO4J_URI` - URI Neo4j бази даних
- `NEO4J_USER` - користувач Neo4j (зазвичай "neo4j")
- `NEO4J_PASSWORD` - пароль Neo4j
- `RADA_API_TOKEN` - токен API Ради України (опціонально)

## Автоматичне налаштування

Railway автоматично:
1. Визначить Python проєкт
2. Встановить залежності з `requirements.txt`
3. Запустить через `Procfile` або `railway.json`

## Порт

Railway автоматично надає змінну `PORT` - додаток її використовує автоматично.

## Перевірка

Після деплою перевірте:
- Health check: `https://your-app.railway.app/health`
- API docs: `https://your-app.railway.app/docs`



