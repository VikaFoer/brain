# Quick Start Guide

## 1. Встановлення

```bash
cd rag_pipeline
pip install -r requirements.txt
```

## 2. Налаштування

```bash
cp .env.example .env
# Відредагуйте .env: додайте OPENAI_API_KEY та DATABASE_URL
```

## 3. Створення бази даних

```bash
# Встановіть pgvector extension
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Запустіть міграцію
psql $DATABASE_URL -f migrations/001_init_pgvector.sql
```

## 4. Запуск пайплайну

### Крок 1: Екстракція тексту
```bash
python -m scripts.extract_text \
    --input data/raw \
    --output data/docs.jsonl \
    --workers 4
```

### Крок 2: Чанкінг
```bash
python -m scripts.chunk_documents \
    --input data/docs.jsonl \
    --output data/chunks.jsonl \
    --chunk-size 8000 \
    --overlap 0.15
```

### Крок 3: Embeddings та збереження
```bash
python -m scripts.embed_chunks \
    --input data/chunks.jsonl \
    --batch-size 100
```

### Крок 4: Пошук
```bash
python -m scripts.search \
    --query "права людини" \
    --topk 10
```

## 5. Тестування

```bash
pytest tests/
```

## Структура даних

### Input: JSONL документів
```json
{
  "doc_id": "abc123",
  "metadata": {
    "title": "Закон про...",
    "act_number": "123/2023",
    "file_path": "data/raw/law.pdf"
  },
  "text": "Повний текст документа..."
}
```

### Output: JSONL чанків
```json
{
  "chunk_id": "abc123_chunk_0",
  "doc_id": "abc123",
  "text": "Текст чанка...",
  "metadata": {
    "section_path": ["Розділ I", "Стаття 1"],
    "chunk_index": 0,
    "char_start": 0,
    "char_end": 500,
    "tokens": 125
  }
}
```

## Масштабування

Для 168,000 документів:
- Використовуйте `--workers 8-16` для екстракції
- Batch size 100-200 для embeddings
- Розбийте на партії по 10,000 документів
- Запускайте в паралель на різних машинах/процесах




