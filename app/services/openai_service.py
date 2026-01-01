"""
Service for working with OpenAI API to extract set elements
"""
from openai import AsyncOpenAI
from typing import Dict, List, Any, Optional
from app.core.config import settings
import logging
import json
import re

logger = logging.getLogger(__name__)

# Try to import wandb for monitoring
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False


class OpenAIService:
    """Service for extracting set elements from legal acts using OpenAI"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL  # For extraction
        self.chat_model = getattr(settings, 'OPENAI_CHAT_MODEL', settings.OPENAI_MODEL)  # For chat
        
        # Chunking settings
        self.max_chunk_size = 40000  # characters per chunk (for input text)
        
        # Token limits based on model capabilities and organization settings
        # GPT-4o supports up to 16384 output tokens
        # These can be adjusted in config.py based on your organization limits
        self.max_response_tokens = getattr(settings, 'OPENAI_MAX_RESPONSE_TOKENS', 16384)
        self.max_chat_tokens = getattr(settings, 'OPENAI_MAX_CHAT_TOKENS', 8192)
        
        # Initialize W&B if enabled (for monitoring API calls)
        self._init_wandb()
    
    def _init_wandb(self):
        """Initialize W&B for monitoring OpenAI API calls"""
        if settings.WANDB_ENABLED and WANDB_AVAILABLE:
            try:
                # Check if wandb is already initialized
                if wandb.run is None:
                    import os
                    if settings.WANDB_API_KEY:
                        os.environ["WANDB_API_KEY"] = settings.WANDB_API_KEY
                    
                    wandb.init(
                        project=settings.WANDB_PROJECT,
                        entity=settings.WANDB_ENTITY,
                        reinit=True,  # Allow reinitialization
                        config={
                            "openai_model": self.model,
                            "openai_chat_model": self.chat_model,
                            "max_response_tokens": self.max_response_tokens,
                            "max_chat_tokens": self.max_chat_tokens,
                        }
                    )
                    logger.info(f"W&B initialized for API monitoring (project: {settings.WANDB_PROJECT})")
                else:
                    logger.debug("W&B already initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize W&B for monitoring: {e}")
                # Continue without W&B
    
    def chunk_legal_text(self, text: str, max_chunk_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Split legal act text into chunks, preferably by articles/sections
        
        Args:
            text: Full text of the legal act
            max_chunk_size: Maximum characters per chunk (default: self.max_chunk_size)
        
        Returns:
            List of chunks with metadata: [{"text": "...", "chunk_index": 0, ...}, ...]
        """
        if not text:
            return []
        
        max_chunk_size = max_chunk_size or self.max_chunk_size
        
        # If text is short enough, return single chunk
        if len(text) <= max_chunk_size:
            return [{
                "text": text,
                "chunk_index": 0,
                "start": 0,
                "end": len(text),
                "total_chunks": 1
            }]
        
        chunks = []
        chunk_index = 0
        start = 0
        
        # Try to split by articles first (Стаття, Статья, Article)
        # Pattern: Стаття N, Статья N, Article N, Стаття N. (with optional number)
        article_pattern = re.compile(r'\n\s*(?:Стаття|Статья|Article|СТАТТЯ|СТАТЬЯ)\s+\d+[\.\s]', re.IGNORECASE)
        
        # Find all article boundaries
        article_matches = list(article_pattern.finditer(text))
        
        if len(article_matches) > 1:
            # Split by articles if we have multiple articles
            logger.info(f"Found {len(article_matches)} article boundaries, splitting by articles")
            
            for i, match in enumerate(article_matches):
                article_start = match.start()
                
                # If this chunk would be too large, split it
                if article_start - start > max_chunk_size and start < article_start:
                    # Need to split before this article
                    while start < article_start:
                        end = min(start + max_chunk_size, article_start)
                        
                        # Try to break at sentence boundary
                        if end < article_start:
                            search_start = max(start, end - 500)
                            for j in range(end - 1, search_start, -1):
                                if text[j] in ['.', '!', '?', '\n']:
                                    end = j + 1
                                    break
                        
                        chunk_text = text[start:end].strip()
                        if chunk_text:
                            chunks.append({
                                "text": chunk_text,
                                "chunk_index": chunk_index,
                                "start": start,
                                "end": end,
                                "total_chunks": None
                            })
                            chunk_index += 1
                        start = end
                
                # Determine end of this article chunk
                if i + 1 < len(article_matches):
                    article_end = article_matches[i + 1].start()
                else:
                    article_end = len(text)
                
                # If article is too large, split it further
                if article_end - start > max_chunk_size:
                    # Split large article into smaller chunks
                    current_start = start
                    while current_start < article_end:
                        current_end = min(current_start + max_chunk_size, article_end)
                        
                        # Try to break at paragraph boundary
                        if current_end < article_end:
                            search_start = max(current_start, current_end - 500)
                            for j in range(current_end - 1, search_start, -1):
                                if text[j] == '\n':
                                    current_end = j + 1
                                    break
                        
                        chunk_text = text[current_start:current_end].strip()
                        if chunk_text:
                            chunks.append({
                                "text": chunk_text,
                                "chunk_index": chunk_index,
                                "start": current_start,
                                "end": current_end,
                                "total_chunks": None
                            })
                            chunk_index += 1
                        current_start = current_end
                    
                    start = article_end
                else:
                    # Article fits in one chunk
                    chunk_text = text[start:article_end].strip()
                    if chunk_text:
                        chunks.append({
                            "text": chunk_text,
                            "chunk_index": chunk_index,
                            "start": start,
                            "end": article_end,
                            "total_chunks": None
                        })
                        chunk_index += 1
                    start = article_end
            
            # Handle remaining text after last article
            if start < len(text):
                remaining_text = text[start:].strip()
                if remaining_text:
                    # If remaining is too large, split it
                    if len(remaining_text) > max_chunk_size:
                        current_start = 0
                        while current_start < len(remaining_text):
                            current_end = min(current_start + max_chunk_size, len(remaining_text))
                            chunk_text = remaining_text[current_start:current_end].strip()
                            if chunk_text:
                                chunks.append({
                                    "text": chunk_text,
                                    "chunk_index": chunk_index,
                                    "start": start + current_start,
                                    "end": start + current_end,
                                    "total_chunks": None
                                })
                                chunk_index += 1
                            current_start = current_end
                    else:
                        chunks.append({
                            "text": remaining_text,
                            "chunk_index": chunk_index,
                            "start": start,
                            "end": len(text),
                            "total_chunks": None
                        })
        else:
            # No article boundaries found, split by size with paragraph awareness
            logger.info("No article boundaries found, splitting by size")
            while start < len(text):
                end = min(start + max_chunk_size, len(text))
                
                # Try to break at paragraph boundary
                if end < len(text):
                    search_start = max(start, end - 1000)
                    for i in range(end - 1, search_start, -1):
                        if text[i] == '\n' and i > start:
                            # Check if it's a paragraph break (double newline or followed by capital)
                            if i + 1 < len(text) and (text[i-1] == '\n' or text[i+1].isupper()):
                                end = i + 1
                                break
                
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "start": start,
                        "end": end,
                        "total_chunks": None
                    })
                    chunk_index += 1
                
                start = end
        
        # Set total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks
        
        logger.info(f"Split text into {total_chunks} chunks (max {max_chunk_size} chars each)")
        return chunks
    
    def merge_extraction_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge extraction results from multiple chunks into a single result
        
        Args:
            results: List of extraction results from different chunks
        
        Returns:
            Merged result with combined elements, categories, subsets, relations
        """
        if not results:
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        
        merged = {
            "categories": [],
            "subsets": [],
            "elements": [],
            "relations": [],
            "metadata": {}
        }
        
        # Track seen items to avoid duplicates
        seen_categories = set()
        seen_subsets = {}  # key: (name, category)
        seen_elements = {}  # key: (type, number)
        seen_relations = {}  # key: (type, target_nreg)
        
        for result in results:
            if not result:
                continue
            
            # Merge categories (unique)
            for cat in result.get("categories", []):
                if cat and cat not in seen_categories:
                    merged["categories"].append(cat)
                    seen_categories.add(cat)
            
            # Merge subsets (unique by name and category)
            for subset in result.get("subsets", []):
                if not subset:
                    continue
                subset_name = subset.get("name", "")
                subset_category = subset.get("category", "")
                key = (subset_name.lower(), subset_category.lower())
                if key not in seen_subsets:
                    merged["subsets"].append(subset)
                    seen_subsets[key] = subset
            
            # Merge elements (unique by type and number)
            for element in result.get("elements", []):
                if not element:
                    continue
                elem_type = element.get("type", "")
                elem_number = element.get("number", "")
                key = (elem_type.lower(), str(elem_number).lower())
                if key not in seen_elements:
                    merged["elements"].append(element)
                    seen_elements[key] = element
            
            # Merge relations (unique by type and target_nreg)
            for relation in result.get("relations", []):
                if not relation:
                    continue
                rel_type = relation.get("type", "")
                target_nreg = relation.get("target_nreg", "")
                key = (rel_type.lower(), str(target_nreg).lower())
                if key not in seen_relations:
                    merged["relations"].append(relation)
                    seen_relations[key] = relation
            
            # Merge metadata (use values from last result, or combine if needed)
            metadata = result.get("metadata", {})
            if metadata:
                # For complexity, use most complex
                if "complexity" in metadata:
                    complexity_levels = {"простий": 1, "середній": 2, "складний": 3}
                    current_level = complexity_levels.get(merged["metadata"].get("complexity", "").lower(), 0)
                    new_level = complexity_levels.get(metadata.get("complexity", "").lower(), 0)
                    if new_level > current_level:
                        merged["metadata"]["complexity"] = metadata.get("complexity")
                
                # For other metadata, use from first or combine
                if "main_category" in metadata and "main_category" not in merged["metadata"]:
                    merged["metadata"]["main_category"] = metadata.get("main_category")
        
        # Update total_elements_found in metadata
        merged["metadata"]["total_elements_found"] = len(merged["elements"])
        
        logger.info(f"Merged {len(results)} extraction results: {len(merged['elements'])} elements, "
                   f"{len(merged['categories'])} categories, {len(merged['subsets'])} subsets, "
                   f"{len(merged['relations'])} relations")
        
        return merged
    
    async def extract_single_chunk(
        self,
        chunk_text: str,
        act_title: str,
        chunk_index: int,
        total_chunks: int,
        categories: List[str]
    ) -> Dict[str, Any]:
        """
        Extract set elements from a single chunk of text
        
        Args:
            chunk_text: Text chunk to process
            act_title: Title of the legal act
            chunk_index: Index of this chunk (0-based)
            total_chunks: Total number of chunks
            categories: List of categories
        
        Returns:
            Extraction result for this chunk
        """
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

ВАЖЛИВО: Виділи ВСІ статті, пункти та підпункти з наданого фрагменту тексту."""
        
        chunk_info = ""
        if total_chunks > 1:
            chunk_info = f"\n\nПримітка: Це частина {chunk_index + 1} з {total_chunks} частин документа. Оброби тільки цю частину."
        
        user_prompt = f"""Проаналізуй наступний фрагмент нормативно-правового акту:

Назва: {act_title}
{chunk_info}

Текст фрагменту:
{chunk_text}

ВАЖЛИВО - Виділи ВСІ елементи множини з цього фрагменту:
1. До яких категорій (множин) належить цей акт
2. Які підмножини можна виділити
3. ВСІ конкретні елементи множини (статті, пункти, підпункти, частини статей) з цього фрагменту
4. Зв'язки з іншими нормативно-правовими актами (якщо є посилання на номери реєстрації)"""
        
        try:
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": self.max_response_tokens
            }
            
            if "o1" in self.model.lower():
                reasoning_effort = getattr(settings, 'OPENAI_REASONING_EFFORT', 'high')
                api_params["reasoning_effort"] = reasoning_effort
            
            response = await self.client.chat.completions.create(**api_params)
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            elements_count = len(result.get("elements", []))
            logger.info(f"Extracted {elements_count} elements from chunk {chunk_index + 1}/{total_chunks} of {act_title}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON for chunk {chunk_index + 1}: {e}")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        except Exception as e:
            logger.error(f"Error extracting elements from chunk {chunk_index + 1}: {e}")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
    
    async def extract_set_elements_chunked(
        self,
        legal_act_text: str,
        act_title: str,
        categories: List[str],
        use_chunking: bool = True
    ) -> Dict[str, Any]:
        """
        Extract set elements using chunking for large documents
        
        Args:
            legal_act_text: Full text of the legal act
            act_title: Title of the legal act
            categories: List of categories
            use_chunking: Whether to use chunking (if False, processes as single chunk)
        
        Returns:
            Merged extraction result from all chunks
        """
        if not legal_act_text:
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        
        # Determine if we need chunking
        text_length = len(legal_act_text)
        needs_chunking = use_chunking and text_length > self.max_chunk_size
        
        if not needs_chunking:
            # Process as single chunk
            return await self.extract_single_chunk(
                legal_act_text,
                act_title,
                chunk_index=0,
                total_chunks=1,
                categories=categories
            )
        
        # Split into chunks
        logger.info(f"Document is large ({text_length} chars), splitting into chunks for {act_title}")
        chunks = self.chunk_legal_text(legal_act_text)
        
        if not chunks:
            logger.warning(f"No chunks created for {act_title}")
            return {
                "categories": [],
                "subsets": [],
                "elements": [],
                "relations": [],
                "metadata": {}
            }
        
        if len(chunks) == 1:
            # Only one chunk, process normally
            return await self.extract_single_chunk(
                chunks[0]["text"],
                act_title,
                chunk_index=0,
                total_chunks=1,
                categories=categories
            )
        
        # Process each chunk
        logger.info(f"Processing {len(chunks)} chunks for {act_title}")
        results = []
        
        for chunk in chunks:
            chunk_result = await self.extract_single_chunk(
                chunk["text"],
                act_title,
                chunk_index=chunk["chunk_index"],
                total_chunks=chunk["total_chunks"],
                categories=categories
            )
            results.append(chunk_result)
        
        # Merge results
        merged_result = self.merge_extraction_results(results)
        
        logger.info(f"Successfully processed {len(chunks)} chunks for {act_title}: "
                   f"{len(merged_result['elements'])} total elements extracted")
        
        return merged_result
    
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
        "complexity": "простий/середній/складний",
        "total_elements_found": "загальна кількість знайдених елементів"
    }
}

КРИТИЧНО ВАЖЛИВО:
- Виділи ВСІ статті, пункти та підпункти з акту
- Не пропускай жодних елементів
- Для Конституції та кодексів виділи ВСІ статті без винятку
- Якщо акт містить 100+ статей, виділи всі 100+"""

        # Use chunking for large documents - it will handle the splitting automatically
        # For smaller documents, chunking will process as single chunk
        try:
            # Try direct extraction first with increased max_tokens
            # Use more text for better extraction (up to 100k chars, chunking will handle if larger)
            text_to_analyze = legal_act_text[:100000] if len(legal_act_text) > 100000 else legal_act_text
            
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

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,  # Lower temperature for more consistent extraction
                "max_tokens": self.max_response_tokens  # Configurable via OPENAI_MAX_RESPONSE_TOKENS (GPT-4o limit: 16384)
            }
            
            # Add reasoning effort only for models that support it (o1 series)
            if "o1" in self.model.lower():
                reasoning_effort = getattr(settings, 'OPENAI_REASONING_EFFORT', 'high')
                api_params["reasoning_effort"] = reasoning_effort
            
            response = await self.client.chat.completions.create(**api_params)
            
            result_text = response.choices[0].message.content
            
            # Check if response might be truncated (incomplete JSON)
            # If response doesn't end with }, it might be truncated
            result_text_stripped = result_text.strip()
            if not result_text_stripped.endswith('}') and not result_text_stripped.endswith('"}'):
                logger.warning(f"Response for {act_title} might be truncated, falling back to chunking")
                # Fallback to chunking
                return await self.extract_set_elements_chunked(legal_act_text, act_title, categories, use_chunking=True)
            
            result = json.loads(result_text)
            
            # Log how many elements were extracted
            elements_count = len(result.get("elements", []))
            logger.info(f"Successfully extracted {elements_count} elements from act: {act_title}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OpenAI response as JSON for {act_title}: {e}")
            logger.info(f"Falling back to chunking for {act_title}")
            # Fallback to chunking if JSON parsing fails (likely due to truncation)
            try:
                return await self.extract_set_elements_chunked(legal_act_text, act_title, categories, use_chunking=True)
            except Exception as chunk_error:
                logger.error(f"Chunking also failed for {act_title}: {chunk_error}")
                return {
                    "categories": [],
                    "subsets": [],
                    "elements": [],
                    "relations": [],
                    "metadata": {}
                }
        except Exception as e:
            logger.error(f"Error extracting elements for {act_title}: {e}")
            # Try chunking as fallback
            logger.info(f"Trying chunking as fallback for {act_title}")
            try:
                return await self.extract_set_elements_chunked(legal_act_text, act_title, categories, use_chunking=True)
            except Exception as chunk_error:
                logger.error(f"Chunking also failed for {act_title}: {chunk_error}")
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
            # Use chat-specific model if available, otherwise use default
            chat_model = getattr(self, 'chat_model', self.model)
            
            # Prepare API call parameters
            api_params = {
                "model": chat_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": self.max_chat_tokens  # Configurable via OPENAI_MAX_CHAT_TOKENS (GPT-4o supports up to 16384)
            }
            
            # Add reasoning effort only for models that support it (o1 series)
            # Note: GPT-5.2-pro doesn't exist yet, and reasoning_effort is for o1 models
            if "o1" in chat_model.lower():
                reasoning_effort = getattr(settings, 'OPENAI_REASONING_EFFORT', 'high')
                api_params["reasoning_effort"] = reasoning_effort
            
            response = await self.client.chat.completions.create(**api_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in database chat: {e}")
            return "Вибачте, сталася помилка при обробці вашого запиту. Перевірте, чи налаштовано OpenAI API ключ."


# Singleton instance
openai_service = OpenAIService()

