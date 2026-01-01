# Інтеграція Weights & Biases (W&B) та Weave

Це керівництво показує, як використовувати W&B та W&B Weave для відстеження експериментів та LLM tracing у Legal Graph System.

## 🚀 Швидкий старт

### 1. Встановлення та логін

```bash
# Встановити wandb
pip install wandb

# Залогінитися (вставити API ключ)
wandb login
```

API ключ можна знайти на [wandb.ai/settings](https://wandb.ai/settings)

### 2. Налаштування

Додайте до `.env`:

```env
WANDB_API_KEY=your-api-key-here
WANDB_PROJECT=legal-graph-system
WANDB_ENABLED=true
WANDB_ENTITY=your-entity-name  # Опціонально
```

### 3. Базовий приклад

```python
import wandb

# Ініціалізація run
run = wandb.init(
    project="legal-graph-system",
    config={
        "model": "gpt-4o",
        "max_tokens": 16384,
    }
)

# Логування метрик
run.log({"accuracy": 0.95, "loss": 0.05})

# Завершення
run.finish()
```

## 📊 Приклади використання

### Приклад 1: Просте відстеження (Quickstart стиль)

```bash
python scripts/example_wandb_tracking.py --example simple
```

Це запустить симуляцію з логуванням метрик, подібно до W&B quickstart guide.

### Приклад 2: Відстеження процесу extraction

```bash
python scripts/example_wandb_tracking.py --example extraction
```

Це відстежить реальний процес обробки legal acts з метриками:
- Кількість елементів на акт
- Кількість категорій
- Час обробки
- Загальна статистика

## 🔧 Інтеграція в коді

### Автоматичне відстеження (OpenAI API calls)

W&B автоматично відстежує виклики OpenAI API через `OpenAIService`:

```python
from app.services.openai_service import openai_service

# Це автоматично логується в W&B (якщо WANDB_ENABLED=true)
result = await openai_service.extract_set_elements(
    legal_act_text=text,
    act_title=title,
    categories=[]
)
```

### Ручне відстеження

```python
import wandb

# Ініціалізація
run = wandb.init(
    project="legal-graph-system",
    config={
        "model": "gpt-4o",
        "temperature": 0.2,
    }
)

# Логування метрик
run.log({
    "elements_extracted": 150,
    "categories_found": 3,
    "processing_time": 2.5,
})

# Логування summary (в кінці)
run.summary.update({
    "total_acts_processed": 100,
    "avg_elements_per_act": 145,
})

# Завершення
run.finish()
```

## 📈 Моніторинг Fine-tuning

При використанні `FineTuningService`, W&B автоматично відстежує:

- Статус fine-tuning job
- Метрики навчання
- Використання токенів
- Вартість

```python
from app.services.fine_tuning_service import FineTuningService

service = FineTuningService()
# Fine-tuning job автоматично логується в W&B
job = service.create_fine_tune_job(...)
```

## 🎯 Dashboard

Перегляньте результати на:

```
https://wandb.ai/{entity}/{project}
```

Наприклад:
```
https://wandb.ai/vikafoer-webmediaform/legal-graph-system
```

## 🔍 Що відстежується

### Автоматично:
- OpenAI API виклики (через autolog)
- Використання токенів
- Вартість API викликів
- Fine-tuning jobs

### Вручну (через run.log):
- Кастомні метрики
- Гіперпараметри
- Артефакти
- Зображення/таблиці

## 💡 Поради

1. **Використовуйте tags** для організації:
   ```python
   wandb.init(tags=["extraction", "legal-acts", "production"])
   ```

2. **Логуйте summary в кінці**:
   ```python
   run.summary.update({"final_accuracy": 0.95})
   ```

3. **Використовуйте config для hyperparameters**:
   ```python
   wandb.init(config={
       "learning_rate": 0.001,
       "batch_size": 32,
   })
   ```

4. **Групуйте пов'язані runs** через entity/project structure

## 🌐 W&B Weave для LLM Tracing

W&B Weave - це toolkit для розробки AI-додатків з відстеженням LLM викликів.

### Встановлення

```bash
pip install wandb weave
```

### Базовий приклад tracing

```python
import weave
from openai import OpenAI

# Initialize weave
weave.init('your-entity/your-project')

# Decorate function to track
@weave.op
def create_completion(message: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": message}
        ],
    )
    return response.choices[0].message.content

# Call - automatically traced
result = create_completion("Hello!")
```

### Приклад з extraction

```bash
python scripts/example_weave_tracing.py --example extraction
```

Це відстежить виклики OpenAI API для extraction з inputs/outputs.

### Переваги Weave:

- **Автоматичне відстеження** всіх LLM викликів
- **Візуалізація** inputs/outputs
- **Debugging** - дивитися що саме надсилається/отримується
- **Evaluation** - оцінка якості відповідей
- **Playground** - інтерактивна розробка prompts

### Weave Service

Використовуйте `WeaveService` для інтеграції:

```python
from app.services.weave_service import weave_service

@weave_service.trace_function
async def my_extraction_function(...):
    # Це автоматично буде traced
    ...
```

## 📚 Додаткові ресурси

- [W&B Documentation](https://docs.wandb.ai/)
- [W&B Python API](https://docs.wandb.ai/ref/python)
- [W&B Quickstart](https://wandb.ai/quickstart)
- [W&B Weave Documentation](https://wandb.ai/weave)
- [W&B Weave Quickstart](https://wandb.ai/weave/quickstart)

