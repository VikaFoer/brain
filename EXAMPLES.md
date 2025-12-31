# Приклади використання API

## 📚 Базові операції

### 1. Отримати всі категорії

```bash
GET /api/categories/
```

Відповідь:
```json
[
  {
    "id": 1,
    "name": "Банки, фінанси, кредит, бюджет",
    "description": null,
    "element_count": 15663
  },
  ...
]
```

### 2. Отримати граф для вибраних категорій

```bash
GET /api/graph/categories?category_ids=1,2,3&depth=2
```

Відповідь:
```json
{
  "nodes": [
    {
      "id": 1,
      "label": "Category",
      "properties": {
        "name": "Банки, фінанси, кредит, бюджет",
        "element_count": 15663
      }
    },
    ...
  ],
  "edges": [
    {
      "source": 1,
      "target": 2,
      "type": "BELONGS_TO",
      "properties": {}
    },
    ...
  ]
}
```

### 3. Обробити нормативно-правовий акт

```bash
POST /api/legal-acts/254к/96-вр/process
```

Це завантажить акт з API Ради, виділить елементи через OpenAI та синхронізує з обома БД.

### 4. Чат про зв'язки

```bash
POST /api/chat/
Content-Type: application/json

{
  "question": "Які зв'язки між банківським та податковим законодавством?",
  "category_ids": [1, 3],
  "context_type": "relations"
}
```

Відповідь:
```json
{
  "answer": "Між банківським та податковим законодавством існують...",
  "context_used": {
    "categories": [...],
    "relations": [...]
  }
}
```

## 🐍 Python приклади

### Завантаження та обробка акту

```python
import asyncio
from app.core.database import SessionLocal
from app.services.processing_service import ProcessingService

async def process_act(nreg: str):
    db = SessionLocal()
    try:
        service = ProcessingService(db)
        act = await service.process_legal_act(nreg)
        print(f"Processed: {act.title}")
    finally:
        db.close()

# Використання
asyncio.run(process_act("254к/96-вр"))
```

### Отримання графа через Neo4j

```python
from app.services.neo4j_service import neo4j_service

# Отримати граф для категорій
graph = neo4j_service.get_category_graph([1, 2, 3], depth=2)
print(f"Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}")

# Отримати зв'язки між категоріями
relations = neo4j_service.get_relations_between_categories(1, 2)
for rel in relations:
    print(f"{rel['source_act']['title']} -> {rel['target_act']['title']}")
```

### Використання OpenAI для аналізу

```python
from app.services.openai_service import openai_service

# Виділити елементи з акту
result = await openai_service.extract_set_elements(
    legal_act_text="Текст акту...",
    act_title="Назва акту",
    categories=["Банки, фінанси, кредит, бюджет"]
)

print(f"Категорії: {result['categories']}")
print(f"Елементи: {len(result['elements'])}")
print(f"Зв'язки: {len(result['relations'])}")
```

## 🔄 Масове завантаження

### Завантаження списку нових актів

```python
import asyncio
from app.services.rada_api import rada_api
from app.core.database import SessionLocal
from app.services.processing_service import ProcessingService

async def load_new_acts():
    db = SessionLocal()
    service = ProcessingService(db)
    
    # Отримати список нових актів
    nregs = await rada_api.get_new_documents_list(days=30)
    
    print(f"Знайдено {len(nregs)} нових актів")
    
    # Обробити кожен (з обмеженням)
    for i, nreg in enumerate(nregs[:10]):  # Перші 10 для прикладу
        print(f"Processing {i+1}/{min(10, len(nregs))}: {nreg}")
        await service.process_legal_act(nreg)
        await asyncio.sleep(7)  # Rate limiting
    
    db.close()

asyncio.run(load_new_acts())
```

## 📊 Аналіз зв'язків

### Знайти всі акти, що посилаються на інший акт

```python
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct, ActRelation

db = SessionLocal()

# Знайти акт
target_act = db.query(LegalAct).filter(LegalAct.nreg == "254к/96-вр").first()

# Знайти всі акти, що посилаються на нього
relations = db.query(ActRelation).filter(
    ActRelation.target_act_id == target_act.id,
    ActRelation.relation_type == "посилається"
).all()

for rel in relations:
    source = db.query(LegalAct).get(rel.source_act_id)
    print(f"{source.title} посилається на {target_act.title}")
```

## 🎯 GraphRAG запити

### Cypher запити до Neo4j

```cypher
// Знайти всі категорії з кількістю актів
MATCH (c:Category)<-[:IN_CATEGORY]-(a:LegalAct)
RETURN c.name, count(a) as act_count
ORDER BY act_count DESC

// Знайти найбільш пов'язані акти
MATCH (a1:LegalAct)-[r]->(a2:LegalAct)
RETURN a1.title, a2.title, count(r) as relation_count
ORDER BY relation_count DESC
LIMIT 10

// Знайти шлях між двома категоріями
MATCH path = (c1:Category {id: 1})-[*..5]-(c2:Category {id: 2})
RETURN path
LIMIT 5
```

