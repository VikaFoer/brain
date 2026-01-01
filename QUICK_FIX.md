# Швидке виправлення: закони не обробляються

## Проблема
В логах Railway НЕ видно "Extracting elements from...", тому кошти не тратяться.

## Швидкий чеклист

### 1. Перевірте чи акти потребують обробки

Відкрийте API в браузері:
```
https://ваш-railway-домен/api/legal-acts/rada-list?limit=10
```

Подивіться:
- Скільки актів з `"is_processed": false`
- Скільки з `"status": "loaded"` (завантажені, але не оброблені)

### 2. Спробуйте обробити один акт вручну

Відкрийте в браузері або через curl:
```
POST https://ваш-railway-домен/api/legal-acts/2145-VIII/process
```

Або через браузер (GET також працює):
```
https://ваш-railway-домен/api/legal-acts/2145-VIII/process
```

**Після цього перевірте логи Railway** - має з'явитися:
```
INFO: Extracting elements from 2145-VIII using OpenAI...
```

### 3. Якщо все одно не працює

Перевірте:
- ✅ `OPENAI_API_KEY` встановлений на Railway (Settings -> Variables)
- ✅ Сервіс перезапущено після додавання ключа
- ✅ В логах НЕ має бути "OpenAI API key is not configured"

### 4. Перевірте базу даних

Якщо маєте доступ до БД:
```sql
-- Скільки актів потребують обробки
SELECT COUNT(*) FROM legal_acts 
WHERE is_processed = false 
  AND text IS NOT NULL;

-- Перевірити один акт
SELECT nreg, title, is_processed, 
       CASE WHEN text IS NULL THEN 'Немає тексту' 
            WHEN LENGTH(text) = 0 THEN 'Порожній текст'
            ELSE 'Є текст' END as text_status
FROM legal_acts 
WHERE nreg = '2145-VIII';
```

## Очікувані логи при успішній обробці

```
INFO: Downloading act 2145-VIII from Rada API...
INFO: Extracting elements from 2145-VIII using OpenAI...
INFO: Successfully extracted X elements from act: ...
INFO: Generating embeddings for 2145-VIII...
INFO: Successfully processed act 2145-VIII
```

## Якщо акти вже оброблені

Щоб переобробити акт:
```
POST https://ваш-railway-домен/api/legal-acts/2145-VIII/process?force_reprocess=true
```

Або через SQL:
```sql
UPDATE legal_acts SET is_processed = false WHERE nreg = '2145-VIII';
```

