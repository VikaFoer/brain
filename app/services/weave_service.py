"""
Service for W&B Weave integration - LLM tracing and evaluation
"""
import os
from typing import Dict, List, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Try to import weave
try:
    import weave
    WEAVE_AVAILABLE = True
except ImportError:
    WEAVE_AVAILABLE = False
    logger.warning("weave not installed. Install with: pip install weave")


class WeaveService:
    """Service for W&B Weave LLM tracing and evaluation"""
    
    def __init__(self):
        self.weave_enabled = settings.WANDB_ENABLED and WEAVE_AVAILABLE
        
        if self.weave_enabled:
            try:
                # Set API key if provided
                if settings.WANDB_API_KEY:
                    os.environ['WANDB_API_KEY'] = settings.WANDB_API_KEY
                
                # Initialize weave
                project_name = f"{settings.WANDB_ENTITY or 'user'}/{settings.WANDB_PROJECT or 'legal-graph-system'}"
                weave.init(project_name)
                
                logger.info(f"Weave initialized for project: {project_name}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Weave: {e}. Continuing without Weave.")
                self.weave_enabled = False
        else:
            logger.info("Weave is disabled or not available")
    
    def trace_function(self, func):
        """
        Decorator to trace a function with Weave
        
        Usage:
            @weave_service.trace_function
            async def my_function(...):
                ...
        """
        if not self.weave_enabled:
            return func
        
        return weave.op(func)
    
    def create_model_class(self):
        """
        Create a Weave Model class for structured extraction
        
        Returns:
            Weave Model class for legal act extraction
        """
        if not self.weave_enabled:
            return None
        
        from textwrap import dedent
        
        class LegalExtractionModel(weave.Model):
            """Weave Model for legal act extraction"""
            
            prompt: weave.Prompt = weave.StringPrompt(dedent("""
                Ти експерт з аналізу нормативно-правових актів України. 
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
                
                У першому повідомленні користувача ти отримаєш JSON дані з текстом акту під міткою 'context', 
                та назву акту під міткою 'title'.
                Твоє завдання - проаналізувати акт та виділити елементи множини.
                
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
                
                ВАЖЛИВО: Виділи ВСІ статті, пункти та підпункти з акту.
            """))
        
        return LegalExtractionModel


# Singleton instance
weave_service = WeaveService() if WEAVE_AVAILABLE else None



