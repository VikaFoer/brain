# Dataset ID для Rada Open Data Portal

## Знайдено Dataset ID!

Згідно з [порталом відкритих даних Верховної Ради](https://data.rada.gov.ua/open/data/laws), dataset ID для нормативно-правових актів:

### **Dataset ID: `laws`**

## Структура даних

Dataset `laws` - це **реєстр відкритих даних**, який містить 47 наборів даних.

### Основні піднабори:

1. **`docs`** - Картки нормативно-правових документів "Законодавство України"
   - URL: https://data.rada.gov.ua/open/data/docs
   - Містить картки всіх документів з NREG

2. **`dict`** - Довідники БД "Законодавство України"
   - URL: https://data.rada.gov.ua/open/data/dict
   - Містить довідники та класифікації

3. **`proj`** - Розподіл документів за комітетами ВР
   - URL: https://data.rada.gov.ua/open/data/proj

## Формати даних

Доступні формати:
- **JSON**: https://data.rada.gov.ua/ogd/zak/laws/list.json
- **CSV**: https://data.rada.gov.ua/ogd/zak/laws/list.csv
- **XML**: https://data.rada.gov.ua/ogd/zak/laws/list.xml

## Встановлення в Railway

### Варіант 1: Використати реєстр "laws"
```
RADA_OPEN_DATA_DATASET_ID=laws
```

Система автоматично спробує отримати дані з піднабору "docs".

### Варіант 2: Використати безпосередньо "docs" (рекомендовано)
```
RADA_OPEN_DATA_DATASET_ID=docs
```

Це напряму отримає картки документів з NREG.

## Перевірка роботи

### Через API endpoint

```bash
curl https://ваш-домен.railway.app/api/legal-acts/test-open-data-api
```

### Безпосередньо через URL

Відкрийте в браузері:
- JSON: https://data.rada.gov.ua/ogd/zak/docs/list.json
- CSV: https://data.rada.gov.ua/ogd/zak/docs/list.csv

## Структура даних в "docs"

Приклад структури JSON:
```json
[
  {
    "nreg": "254к/96-вр",
    "title": "Назва документа",
    "status": "діє",
    ...
  },
  ...
]
```

## Оновлення даних

Згідно з порталом:
- **Частота оновлення**: Щогодини або частіше
- **Остання зміна**: Оновлюється кожні 10 хвилин

## Документація

- **Портал**: https://data.rada.gov.ua/open/data/laws
- **API документація**: https://data.rada.gov.ua/open/main/api/page2
- **Шлях до файлів**: `/ogd/zak/laws/`

## Рекомендації

1. **Використовуйте `docs`** як Dataset ID - це дає прямі картки документів
2. **Система автоматично** спробує `docs` якщо вказано `laws`
3. **Перевіряйте логи** Railway для моніторингу успішності завантаження

