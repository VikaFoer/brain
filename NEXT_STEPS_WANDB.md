# План наступних кроків: W&B інтеграція та Fine-tuning

## ✅ Що вже зроблено

1. ✅ Додано `wandb` та `weave` до requirements.txt
2. ✅ Створено `FineTuningService` з W&B інтеграцією
3. ✅ Створено `WeaveService` для LLM tracing
4. ✅ Додано налаштування W&B у config.py
5. ✅ Створено скрипти для підготовки даних та fine-tuning
6. ✅ Створено приклади використання
7. ✅ Встановлено пакети (wandb, weave)

## 🎯 Наступні кроки

### 1. Налаштування W&B (5 хвилин)

#### 1.1 Отримайте W&B API ключ
1. Перейдіть на [wandb.ai/settings](https://wandb.ai/settings)
2. Скопіюйте ваш API ключ

#### 1.2 Додайте до .env файлу
```env
# W&B Configuration
WANDB_API_KEY=ваш-api-ключ-тут
WANDB_PROJECT=legal-graph-system
WANDB_ENTITY=vikafoer-webmediaform  # ваш entity name
WANDB_ENABLED=true
```

#### 1.3 Перевірте налаштування
```bash
python -c "from app.core.config import settings; print('W&B Project:', settings.WANDB_PROJECT)"
```

### 2. Тестування W&B Weave (10 хвилин)

#### 2.1 Залогініться (якщо ще не зробили)
```bash
python -m wandb login
```
Вставте API ключ коли попросить.

#### 2.2 Запустіть простий приклад tracing
```bash
python scripts/example_weave_tracing.py --example basic
```

#### 2.3 Перевірте dashboard
Перейдіть на: https://wandb.ai/vikafoer-webmediaform/legal-graph-system

### 3. Інтеграція W&B у production код (опціонально)

Якщо хочете відстежувати всі OpenAI виклики автоматично:

#### 3.1 В `openai_service.py` вже є підтримка W&B
Просто встановіть `WANDB_ENABLED=true` у .env

#### 3.2 Для ручного відстеження метрик
Використовуйте `scripts/example_wandb_tracking.py` як приклад

### 4. Підготовка даних для Fine-tuning (30-60 хвилин)

#### 4.1 Перевірте, скільки оброблених актів у вас є
```python
# У Python або через скрипт
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct

db = SessionLocal()
count = db.query(LegalAct).filter(
    LegalAct.is_processed == True,
    LegalAct.extracted_elements.isnot(None)
).count()
print(f"Оброблених актів: {count}")
```

#### 4.2 Підготуйте training data
```bash
# Підготувати дані з бази
python scripts/prepare_finetuning_data.py --output training_data.jsonl

# Обмежити кількість (для тесту)
python scripts/prepare_finetuning_data.py --limit 50 --output training_data.jsonl
```

#### 4.3 Розділіть на training/validation (рекомендовано)
```python
# Простий Python скрипт для розділення
import json
import random

with open('training_data.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

random.shuffle(lines)
split = int(len(lines) * 0.9)

with open('train.jsonl', 'w', encoding='utf-8') as f:
    f.writelines(lines[:split])

with open('validation.jsonl', 'w', encoding='utf-8') as f:
    f.writelines(lines[split:])

print(f'Split: {split} training, {len(lines)-split} validation')
```

### 5. Запуск Fine-tuning (2-4 години + час навчання)

#### 5.1 Перевірте вартість
- GPT-4o-mini: $0.15 / 1M training tokens
- GPT-3.5-turbo: $0.80 / 1M training tokens

Рекомендовано почати з `gpt-4o-mini` (дешевше).

#### 5.2 Запустіть fine-tuning
```bash
python scripts/run_finetuning.py \
    --training-file train.jsonl \
    --validation-file validation.jsonl \
    --upload \
    --base-model gpt-4o-mini \
    --suffix legal-extraction-v1 \
    --monitor
```

#### 5.3 Моніторинг
- Перевіряйте статус у W&B dashboard
- Або через код: `service.get_fine_tune_status(job_id)`

### 6. Використання Fine-tuned моделі (після завершення)

#### 6.1 Отримайте model ID
Після завершення fine-tuning ви отримаєте model ID типу:
```
ft:gpt-4o-mini:your-org:legal-extraction-v1:abc123
```

#### 6.2 Оновіть config
```env
OPENAI_MODEL=ft:gpt-4o-mini:your-org:legal-extraction-v1:abc123
```

Або у config.py:
```python
OPENAI_MODEL: str = "ft:gpt-4o-mini:your-org:legal-extraction-v1:abc123"
```

#### 6.3 Тестування
Порівняйте результати з базовою моделлю та fine-tuned моделлю.

## 📊 Пріоритети

### Високий пріоритет (зробити зараз):
1. ✅ Налаштувати W&B API ключ
2. ✅ Протестувати Weave tracing
3. ✅ Перевірити кількість даних для fine-tuning

### Середній пріоритет (на цьому тижні):
4. ⏳ Підготувати training data
5. ⏳ Запустити перший fine-tuning (з невеликим dataset)

### Низький пріоритет (коли буде час):
6. ⏳ Інтегрувати W&B tracing у production
7. ⏳ Налаштувати автоматичні evaluations
8. ⏳ Створити dashboard для моніторингу

## 🔍 Troubleshooting

### Проблема: "weave not installed"
**Рішення:** Перезапустіть термінал або VS Code

### Проблема: "WANDB_API_KEY not set"
**Рішення:** Додайте ключ до .env файлу

### Проблема: "Not enough training examples"
**Рішення:** Мінімум 10, рекомендовано 50+. Обробіть більше актів через ваш production pipeline.

### Проблема: Fine-tuning дорогий
**Рішення:** 
- Почніть з `gpt-4o-mini` (в 5 разів дешевше)
- Використовуйте менший dataset для тестування
- Перевірте вартість на [OpenAI Pricing](https://openai.com/api/pricing/)

## 📚 Корисні посилання

- [W&B Dashboard](https://wandb.ai/vikafoer-webmediaform)
- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [W&B Weave Documentation](https://wandb.ai/weave)
- [OpenAI Pricing](https://openai.com/api/pricing/)

## 💡 Поради

1. **Почніть з малого**: Спочатку протестуйте на 10-20 прикладах
2. **Використовуйте validation set**: Це допоможе оцінити якість
3. **Моніторте витрати**: Перевіряйте вартість перед запуском на великому dataset
4. **Зберігайте результати**: Порівнюйте різні версії fine-tuned моделей
5. **Документуйте експерименти**: Використовуйте tags та notes у W&B


