# Керівництво з Fine-tuning та інтеграції W&B

Це керівництво описує, як налаштувати fine-tuning OpenAI моделей та інтегрувати Weights & Biases (W&B) для відстеження експериментів.

## 📋 Вміст

1. [Підготовка](#підготовка)
2. [Налаштування W&B](#налаштування-wb)
3. [Підготовка даних](#підготовка-даних)
4. [Запуск Fine-tuning](#запуск-fine-tuning)
5. [Моніторинг](#моніторинг)
6. [Використання fine-tuned моделі](#використання-fine-tuned-моделі)

## 🔧 Підготовка

### 1. Встановлення залежностей

```bash
pip install -r requirements.txt
```

Це встановить `wandb` та інші необхідні бібліотеки.

### 2. Налаштування змінних середовища

Додайте до вашого `.env` файлу або змінних середовища Railway:

```env
# OpenAI API (вже має бути)
OPENAI_API_KEY=sk-...

# Weights & Biases
WANDB_API_KEY=your-wandb-api-key
WANDB_PROJECT=legal-graph-system
WANDB_ENABLED=true
WANDB_ENTITY=your-team-name  # Опціонально
```

### 3. Отримання W&B API ключа

1. Зареєструйтеся на [wandb.ai](https://wandb.ai)
2. Перейдіть до [Settings](https://wandb.ai/settings) → API keys
3. Скопіюйте ваш API ключ
4. Додайте його до `.env` файлу

## 🎯 Налаштування W&B

### Конфігурація в `config.py`

Вже додані наступні налаштування:

```python
WANDB_API_KEY: Optional[str] = None
WANDB_PROJECT: str = "legal-graph-system"
WANDB_ENABLED: bool = True
WANDB_ENTITY: Optional[str] = None
```

### Ініціалізація W&B

W&B автоматично ініціалізується при:
- Створенні `FineTuningService`
- Використанні `OpenAIService` (для моніторингу API викликів)

## 📊 Підготовка даних

### Вимоги до даних

Для fine-tuning потрібні дані в форматі JSONL, де кожен рядок містить:

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### Генерація даних з бази даних

Використовуйте скрипт `prepare_finetuning_data.py`:

```bash
# Підготувати дані з бази (всі оброблені акти)
python scripts/prepare_finetuning_data.py --output training_data.jsonl

# Обмежити кількість прикладів
python scripts/prepare_finetuning_data.py --limit 100 --output training_data.jsonl
```

Скрипт:
1. Завантажує всі оброблені акти з `extracted_elements` з бази даних
2. Створює training examples у форматі OpenAI
3. Зберігає їх у JSONL файл
4. Валідує файл через OpenAI API

### Мінімальні вимоги

- Мінімум 10 прикладів (рекомендовано 50+)
- Кожен приклад має містити коректний JSON
- Рекомендовано мати validation set (10-20% від training set)

### Створення validation set

```bash
# Розділити дані на training та validation
python -c "
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
"
```

## 🚀 Запуск Fine-tuning

### Базовий використання

```bash
python scripts/run_finetuning.py \
    --training-file training_data.jsonl \
    --upload \
    --base-model gpt-4o-mini \
    --monitor
```

### Параметри

- `--training-file`: Шлях до JSONL файлу або OpenAI file ID
- `--validation-file`: Опціонально, шлях до validation файлу
- `--base-model`: Базова модель (рекомендовано: `gpt-4o-mini`, `gpt-3.5-turbo`)
- `--suffix`: Суфікс для імені fine-tuned моделі
- `--upload`: Завантажити локальні файли на OpenAI
- `--monitor`: Відстежувати прогрес до завершення
- `--n-epochs`: Кількість епох (за замовчуванням: автоматично)
- `--batch-size`: Розмір батчу (за замовчуванням: автоматично)
- `--learning-rate`: Множник learning rate (за замовчуванням: автоматично)

### Приклади

#### 1. Простий запуск з моніторингом

```bash
python scripts/run_finetuning.py \
    --training-file training_data.jsonl \
    --upload \
    --monitor
```

#### 2. З validation set та кастомними параметрами

```bash
python scripts/run_finetuning.py \
    --training-file train.jsonl \
    --validation-file validation.jsonl \
    --upload \
    --base-model gpt-4o-mini \
    --suffix legal-extraction \
    --n-epochs 3 \
    --monitor
```

#### 3. Використання вже завантажених файлів

```bash
python scripts/run_finetuning.py \
    --training-file file-abc123 \
    --validation-file file-def456 \
    --base-model gpt-4o-mini \
    --monitor
```

## 📈 Моніторинг

### W&B Dashboard

Після запуску fine-tuning, перейдіть до W&B dashboard:

```
https://wandb.ai/{entity}/{project}
```

Там ви побачите:
- Метрики навчання
- Використання токенів
- Вартість навчання
- Прогрес job'а

### Через код

```python
from app.services.fine_tuning_service import FineTuningService

service = FineTuningService()

# Перевірити статус
status = service.get_fine_tune_status("ftjob-abc123")
print(status)

# Список подій
events = service.list_fine_tune_events("ftjob-abc123")
for event in events:
    print(f"{event['level']}: {event['message']}")
```

### OpenAI Dashboard

Також можна перевіряти статус на [platform.openai.com](https://platform.openai.com/finetune)

## 💰 Вартість

Fine-tuning вартість:
- **gpt-4o-mini**: $0.15 за 1M training tokens, $0.60 за 1M usage tokens
- **gpt-3.5-turbo**: $0.80 за 1M training tokens, $3.00 за 1M usage tokens

Приклад:
- 100 прикладів × 1000 токенів = ~100k tokens
- Training: ~$0.015 (gpt-4o-mini)
- Usage: залежить від використання

## 🎯 Використання fine-tuned моделі

### В config.py

```python
OPENAI_MODEL = "ft:gpt-4o-mini:your-org:suffix:abc123"
```

Або через змінну середовища:

```env
OPENAI_MODEL=ft:gpt-4o-mini:your-org:suffix:abc123
```

### Через код

```python
from app.services.openai_service import openai_service

# Використання fine-tuned моделі для extraction
result = await openai_service.extract_set_elements(
    legal_act_text=text,
    act_title=title,
    categories=[]
)
```

## 🔍 Перевірка якості

Після fine-tuning рекомендується:

1. **Порівняти результати** з базовою моделлю
2. **Протестувати на validation set**
3. **Виміряти метрики** (точність, повнота)
4. **Перевірити вартість** використання

## 🛠 Troubleshooting

### Помилка: "W&B not initialized"

Перевірте:
- `WANDB_ENABLED=true` в `.env`
- `WANDB_API_KEY` встановлений
- `wandb` встановлений: `pip install wandb`

### Помилка: "File validation failed"

- Перевірте формат JSONL файлу
- Кожен рядок має бути валідним JSON
- Перевірте структуру messages

### Помилка: "Insufficient quota"

- Перевірте баланс на OpenAI account
- Перевірте ліміти на [platform.openai.com/settings/organization/limits](https://platform.openai.com/settings/organization/limits)

### Job зависає

- Перевірте статус через `get_fine_tune_status()`
- Подивіться events через `list_fine_tune_events()`
- Перевірте W&B dashboard для деталей

## 📚 Додаткові ресурси

- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [W&B OpenAI Integration](https://docs.wandb.ai/guides/integrations/openai-api)
- [OpenAI Pricing](https://openai.com/api/pricing/)



