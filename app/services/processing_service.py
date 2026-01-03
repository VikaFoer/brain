"""
Service for processing legal acts and synchronizing between databases
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.legal_act import LegalAct, ActCategory, ActRelation
from app.models.category import Category
from app.models.subset import Subset
from app.services.rada_api import rada_api
from app.services.openai_service import openai_service
from app.services.neo4j_service import neo4j_service
from app.services.embeddings_service import embeddings_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for processing legal acts"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_legal_act(self, nreg: str, force_reprocess: bool = False) -> Optional[LegalAct]:
        """
        Process a single legal act: download, extract elements, sync to both DBs
        
        Args:
            nreg: NREG identifier
            force_reprocess: If True, reprocess even if already processed
        
        Returns:
            LegalAct if successful, None otherwise
        """
        
        # Check if already exists and processed
        act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
        
        if act and act.is_processed and not force_reprocess:
            logger.info(f"Act {nreg} already processed, skipping (use force_reprocess=True to reprocess)")
            return act
        
        # If act exists but not processed, check if it's from dataset
        if act and not act.is_processed:
            logger.info(f"Act {nreg} exists but not processed, continuing with processing...")
            
            # If act has dataset_metadata, use it instead of downloading from API
            if act.dataset_metadata:
                logger.info(f"Act {nreg} has dataset metadata, using it for processing...")
                document_json = act.dataset_metadata.copy()
                # Extract text from metadata if available
                text = (document_json.get("text") or document_json.get("Text") or 
                       document_json.get("текст") or act.text)
                card_json = document_json  # Use metadata as card_json
                
                # If no text in metadata, try to get from act.text
                if not text and act.text:
                    text = act.text
                    document_json["text"] = text
            else:
                # Act exists but no metadata - try to download from API
                document_json = None
                card_json = None
                text = None
        else:
            # Act doesn't exist - need to download
            document_json = None
            card_json = None
            text = None
        
        # If we don't have data yet, try to download from Rada API
        # But skip if NREG looks like a generated ID (contains underscore and doesn't have / or -)
        is_generated_id = '_' in nreg and not ('/' in nreg or '-' in nreg)
        
        if not document_json and not is_generated_id:
            # Validate NREG format before processing
            # Check if it looks like a valid NREG (contains / or -)
            if not ('/' in nreg or '-' in nreg) and not nreg.isdigit():
                logger.warning(f"Invalid NREG format: {nreg}. Skipping download.")
                return None
            
            # Download from Rada API
            logger.info(f"Downloading act {nreg} from Rada API...")
            document_json = await rada_api.get_document_json(nreg)
            card_json = await rada_api.get_document_card(nreg)
            text = await rada_api.get_document_text(nreg)
        elif is_generated_id and not document_json:
            # Generated ID but no data in database - cannot process
            logger.error(f"Cannot process generated ID {nreg} - document not found in database and cannot download from API")
            return None
        
        # If document_json is None, try to get text and create minimal structure
        if not document_json:
            if text:
                logger.info(f"Using text format for {nreg} (JSON unavailable)")
                # Create minimal JSON structure from text
                document_json = {
                    "nreg": nreg,
                    "title": nreg,
                    "text": text,
                    "source": "text_only"
                }
                # Try to extract title from text
                if text:
                    lines = text.split('\n')
                    for line in lines[:20]:  # Check first 20 lines
                        line = line.strip()
                        if line and 10 < len(line) < 300 and not line.startswith('№'):
                            document_json["title"] = line
                            break
            elif act and act.dataset_metadata:
                # Use dataset metadata as fallback
                document_json = act.dataset_metadata.copy()
                logger.info(f"Using dataset metadata for {nreg}")
            else:
                logger.error(f"Failed to download {nreg} (both JSON and text unavailable)")
                return None
        
        # Extract title
        title = document_json.get("title", nreg)
        if card_json:
            title = card_json.get("title", title)
        
        # If we got text from document_json, use it
        if "text" in document_json and not text:
            text = document_json.get("text")
        
        # Extract metadata from card_json or document_json
        document_type = None
        status = None
        date_acceptance = None
        date_publication = None
        
        def parse_date(date_str):
            """Parse date string to datetime object"""
            if not date_str:
                return None
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except:
                # Fallback to simple parsing
                try:
                    from datetime import datetime
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%d/%m/%Y"]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except:
                            continue
                except:
                    pass
            return None
        
        # Try to extract from card_json first (more structured)
        if card_json:
            document_type = card_json.get("type", card_json.get("document_type"))
            status = card_json.get("status", card_json.get("state"))
            date_acceptance = parse_date(card_json.get("date_acceptance"))
            date_publication = parse_date(card_json.get("date_publication"))
        
        # Fallback to document_json (if card_json not available)
        if not card_json and document_json:
            document_type = document_json.get("type", document_json.get("document_type"))
            status = document_json.get("status", document_json.get("state"))
            date_acceptance = parse_date(document_json.get("date_acceptance"))
            date_publication = parse_date(document_json.get("date_publication"))
        
        # Create or update act in PostgreSQL
        if not act:
            act = LegalAct(
                nreg=nreg,
                title=title,
                text=text,
                text_json=document_json,
                card_json=card_json,
                document_type=document_type,
                status=status,
                date_acceptance=date_acceptance,
                date_publication=date_publication
            )
            self.db.add(act)
        else:
            act.title = title
            act.text = text
            act.text_json = document_json
            act.card_json = card_json
            if document_type:
                act.document_type = document_type
            if status:
                act.status = status
            if date_acceptance:
                act.date_acceptance = date_acceptance
            if date_publication:
                act.date_publication = date_publication
        
        self.db.commit()
        self.db.refresh(act)
        
        # Extract elements using OpenAI
        if text:
            text_length = len(text) if text else 0
            logger.info(f"Extracting elements from {nreg} using OpenAI... (text length: {text_length} chars)")
            try:
                extracted = await openai_service.extract_set_elements(
                    legal_act_text=text,
                    act_title=title,
                    categories=[]  # TODO: get from DB
                )
                
                # Check if extraction was successful (not empty)
                if extracted and (extracted.get("categories") or extracted.get("elements") or extracted.get("relations")):
                    act.extracted_elements = extracted
                    act.is_processed = True
                    act.processed_at = datetime.utcnow()
                    
                    # Generate embeddings for semantic search
                    logger.info(f"Generating embeddings for {nreg}...")
                    try:
                        embeddings_result = await embeddings_service.generate_embeddings_for_act(
                            text=text,
                            title=title
                        )
                        if embeddings_result and embeddings_result.get("embeddings"):
                            act.embeddings = embeddings_result
                            logger.info(f"Generated {len(embeddings_result.get('embeddings', []))} embeddings for {nreg}")
                        else:
                            logger.warning(f"Failed to generate embeddings for {nreg}")
                    except Exception as e:
                        logger.error(f"Error generating embeddings for {nreg}: {e}")
                        # Don't fail the whole process if embeddings fail
                    
                    # Process categories
                    for cat_name in extracted.get("categories", []):
                        category = self.db.query(Category).filter(Category.name == cat_name).first()
                        if category:
                            # Link to category
                            act_category = ActCategory(
                                act_id=act.id,
                                category_id=category.id
                            )
                            self.db.add(act_category)
                            
                            # Sync to Neo4j
                            try:
                                neo4j_service.link_act_to_category(act.id, category.id)
                            except RuntimeError:
                                logger.warning("Neo4j not configured, skipping sync")
                    
                    # Process subsets
                    for subset_data in extracted.get("subsets", []):
                        subset_name = subset_data.get("name")
                        category_name = subset_data.get("category")
                        
                        if category_name:
                            category = self.db.query(Category).filter(Category.name == category_name).first()
                            if category:
                                subset = self.db.query(Subset).filter(
                                    Subset.name == subset_name,
                                    Subset.category_id == category.id
                                ).first()
                                
                                if not subset:
                                    subset = Subset(
                                        name=subset_name,
                                        category_id=category.id,
                                        description=subset_data.get("description")
                                    )
                                    self.db.add(subset)
                                    self.db.commit()
                                    self.db.refresh(subset)
                                    
                                    # Sync to Neo4j
                                    try:
                                        neo4j_service.create_subset_node(
                                            subset.id,
                                            subset.name,
                                            category.id
                                        )
                                    except RuntimeError:
                                        logger.warning("Neo4j not configured, skipping sync")
                                
                                act.subset_id = subset.id
                                
                                # Sync act to Neo4j
                                try:
                                    neo4j_service.create_legal_act_node(
                                        act.id,
                                        act.nreg,
                                        act.title,
                                        subset.id
                                    )
                                except RuntimeError:
                                    logger.warning("Neo4j not configured, skipping sync")
                    
                    # Process relations
                    for rel_data in extracted.get("relations", []):
                        target_nreg = rel_data.get("target_nreg")
                        if target_nreg:
                            target_act = self.db.query(LegalAct).filter(
                                LegalAct.nreg == target_nreg
                            ).first()
                            
                            if target_act:
                                relation = ActRelation(
                                    source_act_id=act.id,
                                    target_act_id=target_act.id,
                                    relation_type=rel_data.get("type", "посилається"),
                                    description=rel_data.get("description"),
                                    confidence=rel_data.get("confidence", 100)
                                )
                                self.db.add(relation)
                                
                                # Sync to Neo4j
                                try:
                                    neo4j_service.create_relation(
                                        act.id,
                                        target_act.id,
                                        rel_data.get("type", "посилається"),
                                        rel_data.get("description"),
                                        rel_data.get("confidence", 100)
                                    )
                                except RuntimeError:
                                    logger.warning("Neo4j not configured, skipping sync")
                    
                    self.db.commit()
                else:
                    logger.warning(f"Extraction returned empty result for {nreg}")
                    act.is_processed = False
                    act.extracted_elements = None
                    self.db.commit()
            except Exception as e:
                logger.error(f"Error during OpenAI extraction for {nreg}: {e}")
                act.is_processed = False
                act.extracted_elements = None
                self.db.commit()
        else:
            logger.warning(f"No text available for {nreg}, cannot process")
            act.is_processed = False
        
        # Sync to Neo4j if not already synced (only if processed)
        if act.is_processed:
            try:
                neo4j_service.create_legal_act_node(
                    act.id,
                    act.nreg,
                    act.title,
                    act.subset_id
                )
            except RuntimeError:
                logger.warning("Neo4j not configured, skipping sync")
        
        if act.is_processed:
            logger.info(f"Successfully processed act {nreg}")
        else:
            logger.warning(f"Act {nreg} was not fully processed")
        
        return act
    
    async def initialize_categories(self):
        """Initialize categories from the predefined list"""
        
        categories_data = [
            ("Банки, фінанси, кредит, бюджет", 15663),
            ("Будівництво, капітальний ремонт, архітектура", 1276),
            ("Бухгалтерський облік, оподаткування, аудит, статистика, облік і звітність", 4236),
            ("Господарсько (арбітражно)-процесуальне законодавство", 1136),
            ("Державний та суспільний устрій (в т.ч. громадянство, паспортна система, в'їзд-виїзд, адміністративний поділ, органи нагляду та контролю)", 25090),
            ("Житлове законодавство. Житлово-комунальне господарство", 982),
            ("Загальні засади правового регулювання економічного розвитку", 1412),
            ("Законодавство про адміністративну відповідальність", 613),
            ("Кадрові питання. Нагородження", 24023),
            ("Кримінальне, кримінально-процесуальне, кримінально-виконавче законодавство", 1345),
            ("Ліцензування, сертифікація, патентування, метрологія, стандартизація, авторське право", 1948),
            ("Митна діяльність. Зовнішньоекономічні зв'язки (ЗЕД)", 3596),
            ("Міжнародні відносини", 13031),
            ("Наука, освіта, культура", 4683),
            ("Нотаріат, адвокатура", 143),
            ("Охорона здоров'я, сім'я, молодь, спорт, туризм", 3554),
            ("Охорона, безпека, правопорядок, збройні сили, пожежний нагляд. Надзвичайні заходи", 5514),
            ("Підприємства та підприємницька діяльність, інвестиції та антимонопольне законодавство", 2532),
            ("Природні ресурси, охорона оточуючого середовища, земельне законодавство, гідрометеорологія", 2616),
            ("Проекти. Внесення змін і доповнень до нормативних актів. Втрата чинності", 4303),
            ("Промисловість, паливно-енергетичний комплекс", 3369),
            ("Регіональне законодавство", 13),
            ("Сільське господарство, агропромисловий комплекс", 2431),
            ("Соціальне забезпечення, страхування", 4492),
            ("Суд, прокуратура, юстиція. Органи нагляду та контролю", 11372),
            ("Судова практика", 10027),
            ("Торгівля, громадське харчування, побутове обслуговування", 1261),
            ("Транспорт, зв'язок, інформація", 5582),
            ("Трудові відносини, зайнятість населення, охорона праці", 4131),
            ("Цивільне та цивільно-процесуальне законодавство (в т.ч. приватизація, оренда, власність)", 3634),
            ("Цінні папери, фондовий ринок", 949),
            ("Ядерне законодавство. Ліквідація наслідків Чорнобильської катастрофи та інших ядерних аварій та випробувань", 856),
            ("Не визначено", 2860)
        ]
        
        for item in categories_data:
            # Support both old format (name, count) and new format (code, name, count)
            if len(item) == 2:
                name, count = item
                code = None
            elif len(item) == 3:
                code, name, count = item
            else:
                continue
            
            category = self.db.query(Category).filter(Category.name == name).first()
            if not category:
                category = Category(name=name, code=code, element_count=count)
                self.db.add(category)
            else:
                if code is not None:
                    category.code = code
                category.element_count = count
        
        self.db.commit()
        
        # Sync to Neo4j (if configured)
        try:
            from app.core.neo4j_db import neo4j_driver
            if neo4j_driver.get_driver() is not None:
                for category in self.db.query(Category).all():
                    neo4j_service.create_category_node(
                        category.id,
                        category.name,
                        category.element_count
                    )
                logger.info("Categories synced to Neo4j")
            else:
                logger.info("Neo4j not configured, skipping graph sync")
        except Exception as e:
            logger.warning(f"Neo4j sync failed (non-critical): {e}")
        
        logger.info("Categories initialized")


# Singleton instance will be created per request

