# Як переобробити акт (force reprocess)

## Проблема
POST до `/process` повертає 200 OK, але обробка не виконується, бо акт вже позначений як `is_processed=True`.

## Рішення: Використати force_reprocess

### Варіант 1: Через API з параметром

Додайте `?force_reprocess=true` до URL:

```
POST https://ваш-railway-домен/api/legal-acts/1489-III/process?force_reprocess=true
```

Або через браузер:
```
https://ваш-railway-домен/api/legal-acts/1489-III/process?force_reprocess=true
```

### Варіант 2: Перевірити через API спочатку

Перевірте статус акту:
```
GET https://ваш-railway-домен/api/legal-acts/1489-III/details
```

Подивіться на поле `is_processed` - якщо `true`, акт вже оброблений.

### Варіант 3: Через базу даних (якщо маєте доступ)

```sql
-- Перевірити статус
SELECT nreg, title, is_processed, 
       CASE WHEN text IS NULL THEN 'Немає тексту' ELSE 'Є текст' END as has_text
FROM legal_acts 
WHERE nreg = '1489-III';

-- Скинути статус обробки
UPDATE legal_acts 
SET is_processed = false, extracted_elements = NULL 
WHERE nreg = '1489-III';
```

## Перевірка логів після force_reprocess

Після виклику з `force_reprocess=true`, в логах має з'явитися:
```
INFO: Starting background processing for 1489-III
INFO: Extracting elements from 1489-III using OpenAI...
```

Якщо цього немає - перевірте:
1. Чи налаштований OPENAI_API_KEY на Railway
2. Чи є текст у акту (`text IS NOT NULL`)
3. Чи немає інших помилок у логах

