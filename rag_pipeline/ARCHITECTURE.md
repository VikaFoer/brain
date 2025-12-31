# Архітектура RAG Pipeline

## Вибір Vector DB: pgvector

**Обрані pgvector** за наступними причинами:
1. **Інтеграція з PostgreSQL** - не потрібен окремий сервіс, все в одній БД
2. **Простота підтримки** - стандартні SQL запити, міграції через SQL
3. **Production-ready** - використовується в великих системах, добре протестований

## Компоненти

### 1. Ingestion (`src/ingestion/`)
- **extractors.py**: Парсери для PDF, HTML, DOCX, TXT
- **processor.py**: Оркестрація екстракції, генерація doc_id

**Особливості:**
- Детекція сканів (needs_ocr)
- Підтримка різних кодувань для TXT
- Паралельна обробка через ThreadPoolExecutor

### 2. Cleaning (`src/cleaning/`)
- **cleaner.py**: Очистка тексту від мусору

**Видаляє:**
- Номери сторінок
- Колонтитули
- Повторювані заголовки
- Довідкові блоки (виносить в metadata)

### 3. Chunking (`src/chunking/`)
- **splitter.py**: Структурний чанкінг

**Підтримує:**
- Розпізнавання структури: Розділ → Стаття → Частина → Пункт
- Overlap 10-15% між чанками
- Розбиття великих чанків по реченнях
- Збереження section_path в metadata

### 4. Embeddings (`src/embeddings/`)
- **generator.py**: OpenAI embeddings з батчингом

**Особливості:**
- Batch API для економії ($0.065 vs $0.13)
- Rate limiting (60 RPM)
- Retry з exponential backoff
- Прогрес-бари

### 5. Storage (`src/storage/`)
- **dao.py**: Data Access Object для PostgreSQL

**Функції:**
- Idempotent inserts (перевірка chunk_id)
- Batch inserts
- Cosine similarity search

### 6. Retrieval (`src/retrieval/`)
- **searcher.py**: Semantic search

**Підтримує:**
- TopK пошук
- Фільтри по doc_id, section_path
- Similarity threshold

## База даних

### Таблиця `documents`
- doc_id (PK)
- Метадані: title, act_number, date, authority, url
- reference_block (довідковий блок)
- metadata (JSONB)

### Таблиця `chunks`
- chunk_id (PK)
- doc_id (FK)
- chunk_text
- **embedding vector(3072)** - pgvector
- section_path (TEXT[])
- Метадані: chunk_index, char_start, char_end, tokens

### Індекси
- **ivfflat** на embedding для швидкого ANN пошуку
- GIN на section_path для фільтрації
- B-tree на doc_id, act_number, date

## Пайплайн

```
Files → Extract → Clean → Chunk → Embed → Store → Search
```

1. **Extract**: PDF/HTML/DOCX/TXT → JSONL (documents)
2. **Clean**: Видалення мусору, витяг довідкового блоку
3. **Chunk**: Структурний спліт з overlap
4. **Embed**: OpenAI batch API
5. **Store**: PostgreSQL + pgvector
6. **Search**: Cosine similarity

## Масштабування

### Для 168,000 документів:

**Екстракція:**
- 4-8 workers
- ~2-4 години

**Чанкінг:**
- Послідовно (швидко)
- ~1 година

**Embeddings:**
- Batch size 100-200
- Rate limit 60 RPM
- ~50-100 годин (залежить від розміру)
- Можна паралелізувати на кілька процесів

**Рекомендації:**
- Розбити на партії по 10,000 документів
- Запускати на окремих машинах
- Використовувати queue (Redis/RabbitMQ) для координації

