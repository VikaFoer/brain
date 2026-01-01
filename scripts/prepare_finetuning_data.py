"""
Script to prepare training data for fine-tuning from database
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct
from app.services.openai_service import openai_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_training_example(
    act_title: str,
    act_text: str,
    extracted_elements: dict
) -> dict:
    """
    Prepare a single training example in OpenAI fine-tuning format
    
    Args:
        act_title: Title of the legal act
        act_text: Text of the legal act (truncated to reasonable length)
        extracted_elements: Previously extracted elements (ground truth)
    
    Returns:
        Training example in OpenAI format
    """
    # Limit text length for training (use first 30000 chars)
    text_snippet = act_text[:30000] if act_text else ""
    
    system_prompt = """Ти експерт з аналізу нормативно-правових актів України. 
Твоя задача - виділити з тексту акту елементи множини та їх зв'язки.

Категорії (множини):
- Банки, фінанси, кредит, бюджет
- Будівництво, капітальний ремонт, архітектура
- Бухгалтерський облік, оподаткування, аудит, статистика, облік і звітність
- Господарсько (арбітражно)-процесуальне законодавство
- Державний та суспільний устрій
- Житлове законодавство. Житлово-комунальне господарство
- Загальні засади правового регулювання економічного розвитку
- Законодавство про адміністративну відповідальність
- Кадрові питання. Нагородження
- Кримінальне, кримінально-процесуальне, кримінально-виконавче законодавство
- Ліцензування, сертифікація, патентування, метрологія, стандартизація, авторське право
- Митна діяльність. Зовнішньоекономічні зв'язки (ЗЕД)
- Міжнародні відносини
- Наука, освіта, культура
- Нотаріат, адвокатура
- Охорона здоров'я, сім'я, молодь, спорт, туризм
- Охорона, безпека, правопорядок, збройні сили, пожежний нагляд. Надзвичайні заходи
- Підприємства та підприємницька діяльність, інвестиції та антимонопольне законодавство
- Природні ресурси, охорона оточуючого середовища, земельне законодавство, гідрометеорологія
- Проекти. Внесення змін і доповнень до нормативних актів. Втрата чинності
- Промисловість, паливно-енергетичний комплекс
- Регіональне законодавство
- Сільське господарство, агропромисловий комплекс
- Соціальне забезпечення, страхування
- Суд, прокуратура, юстиція. Органи нагляду та контролю
- Судова практика
- Торгівля, громадське харчування, побутове обслуговування
- Транспорт, зв'язок, інформація
- Трудові відносини, зайнятість населення, охорона праці
- Цивільне та цивільно-процесуальне законодавство
- Цінні папери, фондовий ринок
- Ядерне законодавство. Ліквідація наслідків Чорнобильської катастрофи

Поверни результат у форматі JSON з такою структурою:
{
    "categories": ["назва категорії 1", "назва категорії 2"],
    "subsets": [{"name": "назва підмножини", "category": "категорія", "description": "опис"}],
    "elements": [
        {
            "type": "стаття/пункт/підпункт",
            "number": "номер",
            "text": "текст елементу",
            "category": "категорія",
            "subset": "підмножина"
        }
    ],
    "relations": [
        {
            "type": "посилається/змінює/скасовує/доповнює",
            "target_nreg": "номер реєстрації іншого акту",
            "description": "опис зв'язку"
        }
    ],
    "metadata": {
        "main_category": "основна категорія",
        "complexity": "простий/середній/складний",
        "total_elements_found": "загальна кількість знайдених елементів"
    }
}

ВАЖЛИВО: Виділи ВСІ статті, пункти та підпункти з акту."""

    user_prompt = f"""Проаналізуй наступний нормативно-правовий акт:

Назва: {act_title}

Текст:
{text_snippet}

ВАЖЛИВО - Виділи ВСІ елементи множини:
1. До яких категорій (множин) належить цей акт
2. Які підмножини можна виділити
3. ВСІ конкретні елементи множини (статті, пункти, підпункти, частини статей)
4. Зв'язки з іншими нормативно-правовими актами (якщо є посилання на номери реєстрації)"""

    # Format assistant response as JSON string
    assistant_response = json.dumps(extracted_elements, ensure_ascii=False, indent=2)
    
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }


def prepare_training_data_from_db(
    db: Session,
    limit: int = None,
    output_file: str = "training_data.jsonl"
):
    """
    Prepare training data from database
    
    Args:
        db: Database session
        limit: Maximum number of examples to include (None for all)
        output_file: Output JSONL file path
    """
    # Get all processed acts with extracted elements
    query = db.query(LegalAct).filter(
        LegalAct.is_processed == True,
        LegalAct.extracted_elements.isnot(None),
        LegalAct.text.isnot(None)
    )
    
    if limit:
        query = query.limit(limit)
    
    acts = query.all()
    logger.info(f"Found {len(acts)} processed acts with extracted elements")
    
    training_examples = []
    skipped = 0
    
    for act in acts:
        try:
            if not act.text or not act.extracted_elements:
                skipped += 1
                continue
            
            # Check if extracted_elements is valid JSON
            if isinstance(act.extracted_elements, str):
                extracted = json.loads(act.extracted_elements)
            else:
                extracted = act.extracted_elements
            
            # Validate that extracted elements have required structure
            if not isinstance(extracted, dict):
                skipped += 1
                continue
            
            # Create training example
            example = prepare_training_example(
                act_title=act.title,
                act_text=act.text,
                extracted_elements=extracted
            )
            
            training_examples.append(example)
            
        except Exception as e:
            logger.warning(f"Error processing act {act.nreg}: {e}")
            skipped += 1
            continue
    
    logger.info(f"Prepared {len(training_examples)} training examples ({skipped} skipped)")
    
    # Write to JSONL file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in training_examples:
            json_line = json.dumps(example, ensure_ascii=False)
            f.write(json_line + '\n')
    
    logger.info(f"Saved training data to: {output_path}")
    logger.info(f"File size: {output_path.stat().st_size} bytes")
    
    # Note: File validation will happen during upload
    # You can also manually validate using OpenAI CLI:
    # openai tools fine_tunes.prepare_data -f training_data.jsonl
    
    return len(training_examples)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare fine-tuning data from database")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of examples to include"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="training_data.jsonl",
        help="Output JSONL file path"
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        count = prepare_training_data_from_db(
            db=db,
            limit=args.limit,
            output_file=args.output
        )
        logger.info(f"Successfully prepared {count} training examples")
    finally:
        db.close()


if __name__ == "__main__":
    main()

