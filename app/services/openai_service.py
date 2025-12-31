"""
Service for working with OpenAI API to extract set elements
"""
from openai import AsyncOpenAI
from typing import Dict, List, Any, Optional
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for extracting set elements from legal acts using OpenAI"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    async def extract_set_elements(
        self, 
        legal_act_text: str,
        act_title: str,
        categories: List[str]
    ) -> Dict[str, Any]:
        """
        Extract set elements from legal act text
        
        Returns:
            {
                "elements": [...],  # Виділені елементи множини
                "categories": [...],  # До яких категорій належить
                "subsets": [...],  # До яких підмножин належить
                "relations": [...],  # Зв'язки з іншими актами
                "metadata": {...}
            }
        """
        if not self.client:
            logger.warning("OpenAI API key is not configured. Cannot extract elements.")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        
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
        "complexity": "простий/середній/складний"
    }
}"""

        # Use more text for better extraction (up to 50k chars for important documents)
        text_limit = 50000  # Increased from 15k to capture more elements
        text_to_analyze = legal_act_text[:text_limit]
        
        user_prompt = f"""Проаналізуй наступний нормативно-правовий акт:

Назва: {act_title}

Текст:
{text_to_analyze}

ВАЖЛИВО - Виділи ВСІ елементи множини:
1. До яких категорій (множин) належить цей акт
2. Які підмножини можна виділити
3. ВСІ конкретні елементи множини (статті, пункти, підпункти, частини статей)
   - Не пропускай жодної статті, якщо вона є в акті
   - Виділи всі пункти та підпункти
   - Для Конституції та великих актів - виділи ВСІ статті
4. Зв'язки з іншими нормативно-правовими актами (якщо є посилання на номери реєстрації)

Примітка: Якщо акт містить багато статей (наприклад, Конституція), виділи ВСІ статті, а не тільки перші кілька."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            logger.info(f"Successfully extracted elements from act: {act_title}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        except Exception as e:
            logger.error(f"Error extracting elements: {e}")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
    
    async def analyze_relations(
        self,
        act1_title: str,
        act1_text: str,
        act2_title: str,
        act2_text: str
    ) -> Dict[str, Any]:
        """Analyze relations between two legal acts"""
        if not self.client:
            raise RuntimeError("OpenAI API key is not configured.")
        
        system_prompt = """Ти експерт з аналізу зв'язків між нормативно-правовими актами.
Визнач тип зв'язку між двома актами та його характеристику."""

        user_prompt = f"""Проаналізуй зв'язок між двома актами:

Акт 1: {act1_title}
{act1_text[:5000]}

Акт 2: {act2_title}
{act2_text[:5000]}

Визнач:
1. Тип зв'язку (посилається, змінює, скасовує, доповнює, реалізує, тощо)
2. Напрямок зв'язку (односторонній/двосторонній)
3. Силу зв'язку (сильний/середній/слабкий)

Поверни JSON:
{{
    "relation_type": "тип зв'язку",
    "direction": "односторонній/двосторонній",
    "strength": "сильний/середній/слабкий",
    "description": "детальний опис зв'язку",
    "confidence": 0-100
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error analyzing relations: {e}")
            return {
                "relation_type": "unknown",
                "direction": "unknown",
                "strength": "unknown",
                "description": "",
                "confidence": 0
            }
    
    async def chat_about_relations(
        self,
        user_question: str,
        context: Dict[str, Any]
    ) -> str:
        """Chat about relations between sets using context"""
        if not self.client:
            raise RuntimeError("OpenAI API key is not configured.")
        
        system_prompt = """Ти експерт з аналізу нормативно-правових актів України та їх зв'язків.
Ти допомагаєш користувачам розуміти зв'язки між різними категоріями законодавства та їх елементами."""

        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        
        user_prompt = f"""Контекст для аналізу:
{context_str}

Питання користувача: {user_question}

Відповідай українською мовою, детально та з прикладами."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return "Вибачте, сталася помилка при обробці вашого запиту."
    
    async def chat_about_database(
        self,
        user_question: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Chat about database content - acts, categories, relations, elements"""
        if not self.client:
            raise RuntimeError("OpenAI API key is not configured.")
        
        system_prompt = """Ти експерт-асистент для системи аналізу нормативно-правових актів України.

Твоя задача - відповідати на питання користувачів про:
1. Нормативно-правові акти в базі даних (їх назви, типи, статуси, дати)
2. Категорії законодавства та їх елементи
3. Зв'язки між актами та категоріями
4. Статистику обробки даних
5. Елементи множин, виділені з актів (статті, пункти, підпункти)

ВАЖЛИВО:
- УВАЖНО прочитай весь наданий контекст, включаючи extracted_elements
- Використовуй дані з виділених елементів (статті, пункти) для відповіді на питання
- Якщо в контексті є extracted_elements з релевантними статтями - використовуй їх!
- Надавай конкретні приклади з контексту (NREG, назви актів, номери статей)
- Якщо в контексті немає відповіді, чесно скажи про це
- Відповідай українською мовою
- Буди детальним та корисним
- Якщо питання стосується функцій держави, прав людини, конституційних норм - шукай в extracted_elements!"""

        # Build messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        
        # Add current context and question
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        
        user_prompt = f"""Дані з бази даних:
{context_str}

Питання користувача: {user_question}

Відповідай на основі наданих даних. Якщо потрібної інформації немає в контексті, повідом про це."""

        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in database chat: {e}")
            return "Вибачте, сталася помилка при обробці вашого запиту. Перевірте, чи налаштовано OpenAI API ключ."


# Singleton instance
openai_service = OpenAIService()

