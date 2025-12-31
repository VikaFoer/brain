# Автоматичне завантаження документів з Rada API

## Опис

Два скрипти для автоматичного завантаження та обробки всіх документів з https://data.rada.gov.ua:

1. **`auto_download_all.py`** - одноразове завантаження всіх документів
2. **`auto_download_continuous.py`** - неперервне завантаження нових документів

## Використання

### 1. Одноразове завантаження всіх документів

```bash
python scripts/auto_download_all.py --workers 5
```

**Параметри:**
- `--workers N` - кількість паралельних робочих процесів (default: 5)
- `--no-resume` - не пропускати вже оброблені документи
- `--limit N` - обмежити кількість документів (для тестування)

**Особливості:**
- Автоматично пропускає вже оброблені документи
- Дотримується rate limits Rada API (6 секунд між запитами)
- Логує прогрес у консоль та файл `auto_download.log`
- Зберігає список невдалих NREG у `failed_nregs.txt`
- Показує ETA та швидкість обробки

**Приклад виводу:**
```
Processing documents: 45%|████▌     | 4500/10000 [02:15<02:45, processed=4500, failed=12]
```

### 2. Неперервне завантаження (фоновий режим)

```bash
python scripts/auto_download_continuous.py --workers 5 --interval 24
```

**Параметри:**
- `--workers N` - кількість паралельних робочих процесів (default: 5)
- `--interval HOURS` - інтервал перевірки нових документів (default: 24)

**Особливості:**
- Працює в фоні, перевіряє нові документи періодично
- Обробляє тільки нові документи (за останні 30 днів)
- Логує у файл `auto_download_continuous.log`
- Graceful shutdown (Ctrl+C)

**Запуск у фоні (Linux/Mac):**
```bash
nohup python scripts/auto_download_continuous.py --workers 5 --interval 24 > output.log 2>&1 &
```

**Запуск у фоні (Windows PowerShell):**
```powershell
Start-Process python -ArgumentList "scripts/auto_download_continuous.py", "--workers", "5", "--interval", "24" -WindowStyle Hidden
```

## Що робить скрипт

Для кожного документа:

1. **Перевірка** - чи вже оброблено в БД
2. **Завантаження** - отримання з Rada API (JSON, card, text)
3. **Обробка** - через `ProcessingService`:
   - Екстракція елементів через OpenAI
   - Генерація embeddings
   - Збереження в PostgreSQL
   - Синхронізація з Neo4j (якщо налаштовано)

## Налаштування

Переконайтеся, що в `.env` встановлено:

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
RADA_API_BASE_URL=https://data.rada.gov.ua
RADA_API_DELAY=6.0  # секунд між запитами
```

## Rate Limits

Скрипт автоматично дотримується rate limits:
- **Rada API**: 6 секунд між запитами (налаштовується через `RADA_API_DELAY`)
- **OpenAI**: автоматичний retry з exponential backoff
- **База даних**: коміти після кожного батчу

## Моніторинг

### Логи

- `auto_download.log` - для одноразового завантаження
- `auto_download_continuous.log` - для неперервного завантаження

### Статистика

Скрипт показує:
- Загальна кількість документів
- Оброблено
- Пропущено (вже оброблені)
- Невдалі
- Швидкість обробки (docs/sec)
- ETA (estimated time to arrival)

### Перевірка прогресу

```sql
-- Скільки документів оброблено
SELECT COUNT(*) FROM legal_acts WHERE is_processed = true;

-- Скільки документів з embeddings
SELECT COUNT(*) FROM legal_acts WHERE embeddings IS NOT NULL;

-- Останні оброблені документи
SELECT nreg, title, processed_at 
FROM legal_acts 
WHERE is_processed = true 
ORDER BY processed_at DESC 
LIMIT 10;
```

## Рекомендації

### Для 168,000 документів:

1. **Перший запуск** - використайте `auto_download_all.py`:
   ```bash
   python scripts/auto_download_all.py --workers 5
   ```
   - Займе ~50-100 годин (залежить від розміру документів)
   - Можна запустити на сервері та залишити працювати

2. **Подальше оновлення** - використайте `auto_download_continuous.py`:
   ```bash
   python scripts/auto_download_continuous.py --workers 5 --interval 24
   ```
   - Перевіряє нові документи щодня
   - Обробляє тільки нові

### Оптимізація

- **Більше workers** = швидше, але більше навантаження на API
- Рекомендовано: 5-10 workers для Rada API
- Для OpenAI embeddings: batch size налаштовується в `.env`

### Обробка помилок

- Невдалі документи зберігаються у `failed_nregs.txt`
- Можна повторити обробку:
  ```bash
  # Вручну обробити невдалі
  python -c "
  from app.core.database import SessionLocal
  from app.services.processing_service import ProcessingService
  import asyncio
  
  db = SessionLocal()
  service = ProcessingService(db)
  
  with open('failed_nregs.txt') as f:
      nregs = [line.strip() for line in f]
  
  for nreg in nregs:
      asyncio.run(service.process_legal_act(nreg))
  "
  ```

## Troubleshooting

### Помилка: "OPENAI_API_KEY not set"
- Перевірте `.env` файл
- Переконайтеся, що змінні завантажуються

### Помилка: "DATABASE_URL not set"
- Налаштуйте PostgreSQL connection string
- Перевірте підключення: `psql $DATABASE_URL`

### Багато невдалих документів
- Перевірте логи на деталі помилок
- Можливо, деякі документи недоступні на Rada API
- Спробуйте обробити їх вручну через admin panel

### Повільна обробка
- Перевірте rate limits
- Зменшіть кількість workers
- Перевірте швидкість інтернет-з'єднання

