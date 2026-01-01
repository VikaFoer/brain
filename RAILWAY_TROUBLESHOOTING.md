# Діагностика проблеми обробки законів на Railway

## Проблема
Закони не обробляються, кошти з OpenAI API не тратяться.

## Швидка перевірка на Railway

### 1. Перевірте змінні середовища

**Railway Dashboard → Ваш проект → Settings → Variables**

Обов'язково мають бути:
- ✅ `OPENAI_API_KEY` - ваш API ключ від OpenAI
- ✅ `DATABASE_URL` - URL бази даних PostgreSQL

**Якщо OPENAI_API_KEY відсутній:**
1. Додайте змінну `OPENAI_API_KEY` з вашим ключем
2. Перезапустіть сервіс (Railway → Deployments → Redeploy)

### 2. Перевірте логи на Railway

**Railway → Ваш проект → Deploy Logs або Runtime Logs**

Шукайте ці повідомлення:

#### ✅ Хороші логи (обробка працює):
```
INFO: Extracting elements from {nreg} using OpenAI...
INFO: Successfully extracted {count} elements from act: {title}
```

#### ❌ Поганих логів (проблеми):

**Якщо бачите:**
```
WARNING: OpenAI API key is not configured. Cannot extract elements.
```
→ **Проблема:** `OPENAI_API_KEY` не налаштований або неправильний

**Якщо бачите:**
```
WARNING: Extraction returned empty result for {nreg}
ERROR: Failed to parse OpenAI response as JSON: ...
```
→ **Проблема:** API викликається, але відповідь обрізана або помилкова
→ **Рішення:** Вже додано chunking для цього

**Якщо НЕ бачите:**
```
INFO: Extracting elements from {nreg} using OpenAI...
```
→ **Проблема:** `extract_set_elements` не викликається взагалі
→ Можливі причини:
  - Акти вже `is_processed=True`
  - Немає тексту (`text IS NULL`)
  - `process_legal_act()` не викликається

### 3. Перевірте через API

Відкрийте ваш API на Railway (наприклад: `https://your-app.up.railway.app/api/status`)

Або через curl:
```bash
curl https://your-app.up.railway.app/api/status
```

### 4. Перевірте базу даних

Якщо маєте доступ до бази даних:

```sql
-- Скільки актів потребують обробки
SELECT COUNT(*) 
FROM legal_acts 
WHERE is_processed = false 
  AND text IS NOT NULL;

-- Скільки вже оброблено
SELECT COUNT(*) 
FROM legal_acts 
WHERE is_processed = true;

-- Перевірити один акт
SELECT nreg, title, is_processed, 
       CASE WHEN text IS NULL THEN 'Немає тексту' ELSE 'Є текст' END as has_text
FROM legal_acts 
LIMIT 10;
```

### 5. Спробуйте обробити акт вручну через API

```bash
# Замініть {nreg} на реальний номер
curl -X POST https://your-app.up.railway.app/api/legal-acts/{nreg}/process
```

Або через браузер:
```
https://your-app.up.railway.app/api/legal-acts/254к/96-ВР/process
```

Подивіться логи Railway після цього виклику.

## Типові проблеми та рішення

### Проблема 1: API ключ не налаштований

**Симптоми:**
- В логах: "OpenAI API key is not configured"
- Кошти не тратяться

**Рішення:**
1. Railway → Settings → Variables
2. Додайте `OPENAI_API_KEY=sk-...`
3. Перезапустіть сервіс

### Проблема 2: Акти вже оброблені

**Симптоми:**
- Всі акти мають `is_processed=true`
- Обробка не запускається

**Рішення:**
Обробка запускається тільки для актів з `is_processed=false`.

Щоб переобробити:
```sql
UPDATE legal_acts SET is_processed = false WHERE nreg = '254к/96-ВР';
```

Або використайте `force_reprocess=True` в API:
```bash
curl -X POST "https://your-app.up.railway.app/api/legal-acts/254к/96-ВР/process?force_reprocess=true"
```

### Проблема 3: Немає тексту у актів

**Симптоми:**
- Акти в базі, але `text IS NULL`
- Обробка не запускається (потрібен текст)

**Рішення:**
Перевірте чи правильно завантажуються акти з Rada API.

### Проблема 4: Обробка не запускається автоматично

**Симптоми:**
- Акти не обробляються автоматично
- Потрібно викликати `/process` вручну

**Пояснення:**
Обробка запускається тільки коли:
- Викликається endpoint `/api/legal-acts/{nreg}/process`
- Або запускається скрипт обробки

**Автоматична обробка:**
Якщо потрібна автоматична обробка всіх актів, використайте:
- Скрипт `scripts/process_all_npa_overnight.py`
- Або endpoint `/api/legal-acts/process-all-overnight`

## Контрольний список

- [ ] `OPENAI_API_KEY` встановлений на Railway
- [ ] Сервіс перезапущено після додавання ключа
- [ ] В логах є повідомлення "Extracting elements..."
- [ ] Є акти з `is_processed=false` та `text IS NOT NULL`
- [ ] Кошти тратяться на platform.openai.com (перевірте usage)

## Як перевірити використання OpenAI API

1. Перейдіть на [platform.openai.com/usage](https://platform.openai.com/usage)
2. Подивіться на графік використання
3. Якщо використання = 0 → API не викликається
4. Якщо є використання → API працює, перевірте логи для деталей

## Наступні кроки після виправлення

1. Перевірте що обробка працює (логи Railway)
2. Перевірте що кошти тратяться (OpenAI dashboard)
3. Перевірте результати в базі даних (`extracted_elements` заповнені)
4. Якщо все працює - можна переходити до fine-tuning!

