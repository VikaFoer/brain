# RAG Pipeline для індексації НПА України

Production-ready пайплайн для обробки 168,000 нормативно-правових актів та створення embeddings для RAG.

## Архітектура

```
raw files (PDF/HTML/DOCX/TXT)
    ↓
[extract_text] → JSONL (documents)
    ↓
[chunk_documents] → JSONL (chunks)
    ↓
[embed_chunks] → PostgreSQL + pgvector
    ↓
[search] → topK results
```

## Встановлення

```bash
# Встановити залежності
pip install -r requirements.txt

# Налаштувати .env
cp .env.example .env
# Відредагувати .env: OPENAI_API_KEY, DATABASE_URL

# Створити базу даних та схему
psql $DATABASE_URL -f migrations/001_init_pgvector.sql
```

## Використання

### 1. Екстракція тексту з файлів

```bash
python -m scripts.extract_text \
    --input data/raw \
    --output data/docs.jsonl \
    --workers 4
```

### 2. Чанкінг документів

```bash
python -m scripts.chunk_documents \
    --input data/docs.jsonl \
    --output data/chunks.jsonl \
    --chunk-size 8000 \
    --overlap 0.15
```

### 3. Генерація embeddings та збереження

```bash
python -m scripts.embed_chunks \
    --input data/chunks.jsonl \
    --batch-size 100 \
    --workers 4
```

### 4. Пошук

```bash
python -m scripts.search \
    --query "права людини" \
    --topk 10
```

## Структура проекту

```
rag_pipeline/
├── src/
│   ├── ingestion/      # Парсинг файлів
│   ├── cleaning/        # Очистка тексту
│   ├── chunking/        # Структурний спліттер
│   ├── embeddings/      # OpenAI клієнт + батчинг
│   ├── storage/         # pgvector схема + DAO
│   ├── retrieval/      # Пошук topK
│   └── utils/           # Логування, конфіг, ретраї
├── scripts/             # CLI entrypoints
├── migrations/          # SQL міграції
├── tests/               # Тести
└── data/                # Дані (gitignored)
```

## Конфігурація

Всі налаштування в `.env`:
- `OPENAI_API_KEY` - ключ OpenAI
- `DATABASE_URL` - PostgreSQL connection string
- `EMBED_MODEL` - модель embeddings (default: text-embedding-3-large)
- `CHUNK_SIZE` - розмір чанка в токенах (default: 8000)
- `OVERLAP` - overlap між чанками (default: 0.15)
- `BATCH_SIZE` - розмір батчу для embeddings (default: 100)
- `TOPK` - кількість результатів пошуку (default: 10)




