# Використання API порталу відкритих даних Верховної Ради

## Огляд

Додано підтримку [API порталу відкритих даних Верховної Ради України](https://data.rada.gov.ua/open/main/api) для отримання всіх нормативно-правових актів через структуровані набори даних з ідентифікаторами.

## Переваги нового підходу

1. **Структуровані дані** - отримуємо дані у форматах JSON/CSV/XML замість парсингу HTML
2. **Надійність** - API надає актуальні дані з датою оновлення
3. **Ефективність** - один запит замість багатьох HTML сторінок
4. **Метадані** - додаткова інформація про набори даних

## Як це працює

### 1. Знаходження набору даних

Система автоматично шукає набір даних з нормативно-правовими актами в каталозі порталу відкритих даних:

- Перевіряє каталог за адресою `https://data.rada.gov.ua/ogd/`
- Шукає набори даних за ключовими словами: "законодавство", "нормативно-правові", "нпа", "закони", "база даних"
- Витягує ідентифікатор набору даних (ID або GUID)

### 2. Отримання даних

Після знаходження ідентифікатора, система отримує дані у форматі JSON:

```
https://data.rada.gov.ua/open/data/{dataset_id}.json
```

### 3. Витягування NREG

Система автоматично витягує NREG (номери реєстрації) з отриманих даних, перевіряючи різні можливі назви полів:
- `nreg`, `NREG`
- `number`, `id`, `identifier`, `code`

## Налаштування

### Автоматичне знаходження (рекомендовано)

Система автоматично знайде набір даних при першому використанні. Нічого налаштовувати не потрібно.

### Ручне вказання dataset ID

Якщо ви знаєте точний ID набору даних, можете вказати його в `.env`:

```env
RADA_OPEN_DATA_DATASET_ID=12345
```

Щоб знайти ID:
1. Відвідайте https://data.rada.gov.ua/ogd/
2. Знайдіть набір даних "База даних нормативно-правових документів 'Законодавство України'"
3. Скопіюйте ID з URL або метаданих

## Використання

### Автоматичне використання

Система автоматично використовує API порталу відкритих даних як **перший fallback** метод, якщо HTML парсинг не працює:

```python
# В app/services/rada_api.py метод get_all_documents_list()
# автоматично використає open data API якщо пагінація не працює
nregs = await rada_api.get_all_documents_list(limit=None)
```

### Тестування API

Використайте тестовий endpoint для перевірки роботи:

```bash
# Через curl
curl http://localhost:8000/api/legal-acts/test-open-data-api

# Або через браузер
http://localhost:8000/api/legal-acts/test-open-data-api
```

Відповідь:
```json
{
  "status": "success",
  "dataset_id": "12345",
  "nregs_count": 50000,
  "sample_nregs": ["254к/96-вр", "4170-IX", ...],
  "message": "Successfully fetched 50000 NREG identifiers from open data portal"
}
```

### Пряме використання

```python
from app.services.rada_api import rada_api

# Знайти dataset ID
dataset_id = await rada_api.find_legal_acts_dataset_id()

# Отримати всі NREG
nregs = await rada_api.get_all_nregs_from_open_data(dataset_id=dataset_id)

# Або з вказаним ID
nregs = await rada_api.get_all_nregs_from_open_data(dataset_id="12345")
```

## Формати даних

API підтримує три формати:

| Формат | URL | Опис |
|--------|-----|------|
| JSON | `.../data/{id}.json` | Структуровані дані (рекомендовано) |
| CSV | `.../data/{id}.csv` | Табличний формат |
| XML | `.../data/{id}.xml` | XML структура |

Система автоматично спробує JSON, потім CSV якщо JSON не працює.

## Оновлення даних

API повертає дату останнього оновлення в HTTP заголовку `Last-Modified`. 

Для оптимізації в майбутньому можна використовувати заголовок `If-Modified-Since` для перевірки, чи потрібно оновлювати дані.

## Порядок використання методів

Система використовує наступний порядок спроб отримання списку НПА:

1. **HTML пагінація** (`/laws/main/r?page=...`) - основний метод
2. **Open Data Portal API** - перший fallback (структуровані дані)
3. **Нові документи** (`/laws/main/n`) - другий fallback
4. **Оновлені документи** (`/laws/main/r`) - третій fallback
5. **База даних** - останній fallback (використовує вже завантажені NREG)

## Приклади використання

### Завантаження всіх НПА через open data API

```python
from app.services.rada_api import rada_api

# Отримати всі NREG через open data portal
nregs = await rada_api.get_all_nregs_from_open_data()

print(f"Знайдено {len(nregs)} нормативно-правових актів")
```

### Отримання конкретного набору даних

```python
# Отримати набір даних у JSON форматі
dataset = await rada_api.get_open_data_dataset("12345", format="json")

# Або CSV
dataset = await rada_api.get_open_data_dataset("12345", format="csv")
```

### Перегляд каталогу наборів даних

```python
# Отримати каталог наборів даних
catalog = await rada_api.get_open_data_catalog()

# Каталог містить список всіх доступних наборів даних
```

## Документація API

Повна документація API порталу відкритих даних:
- https://data.rada.gov.ua/open/main/api
- https://data.rada.gov.ua/ogd/ - каталог наборів даних

## Troubleshooting

### Помилка: "Could not find legal acts dataset ID"

**Рішення:**
1. Перевірте доступність https://data.rada.gov.ua/ogd/
2. Знайдіть ID набору даних вручну та вкажіть в `.env`:
   ```env
   RADA_OPEN_DATA_DATASET_ID=ваш_id
   ```

### Помилка: "Could not extract NREG identifiers"

**Рішення:**
Структура даних може відрізнятися. Перевірте структуру набору даних:
```bash
curl https://data.rada.gov.ua/open/data/{dataset_id}.json | jq '.[0]'
```

Потім оновіть метод `get_all_nregs_from_open_data()` для підтримки вашої структури.

### Дані не оновлюються

Перевірте заголовок `Last-Modified` у відповіді API та реалізуйте кешування з перевіркою дати оновлення.

## Майбутні покращення

- [ ] Кешування dataset ID після першого знаходження
- [ ] Використання `If-Modified-Since` для оптимізації
- [ ] Підтримка пагінації для великих наборів даних
- [ ] Автоматичне оновлення при зміні даних
- [ ] Підтримка інших форматів (XML)

