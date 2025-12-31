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
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for processing legal acts"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_legal_act(self, nreg: str) -> Optional[LegalAct]:
        """Process a single legal act: download, extract elements, sync to both DBs"""
        
        # Check if already exists
        act = self.db.query(LegalAct).filter(LegalAct.nreg == nreg).first()
        
        if act and act.is_processed:
            logger.info(f"Act {nreg} already processed")
            return act
        
        # Download from Rada API
        logger.info(f"Downloading act {nreg} from Rada API...")
        document_json = await rada_api.get_document_json(nreg)
        card_json = await rada_api.get_document_card(nreg)
        text = await rada_api.get_document_text(nreg)
        
        if not document_json:
            logger.error(f"Failed to download {nreg}")
            return None
        
        # Extract title
        title = document_json.get("title", nreg)
        if card_json:
            title = card_json.get("title", title)
        
        # Create or update act in PostgreSQL
        if not act:
            act = LegalAct(
                nreg=nreg,
                title=title,
                text=text,
                text_json=document_json,
                card_json=card_json
            )
            self.db.add(act)
        else:
            act.title = title
            act.text = text
            act.text_json = document_json
            act.card_json = card_json
        
        self.db.commit()
        self.db.refresh(act)
        
        # Extract elements using OpenAI
        if text:
            logger.info(f"Extracting elements from {nreg} using OpenAI...")
            extracted = await openai_service.extract_set_elements(
                legal_act_text=text,
                act_title=title,
                categories=[]  # TODO: get from DB
            )
            
            act.extracted_elements = extracted
            act.is_processed = True
            act.processed_at = datetime.utcnow()
            
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
                    neo4j_service.link_act_to_category(act.id, category.id)
            
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
                            neo4j_service.create_subset_node(
                                subset.id,
                                subset.name,
                                category.id
                            )
                        
                        act.subset_id = subset.id
                        
                        # Sync act to Neo4j
                        neo4j_service.create_legal_act_node(
                            act.id,
                            act.nreg,
                            act.title,
                            subset.id
                        )
            
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
                        neo4j_service.create_relation(
                            act.id,
                            target_act.id,
                            rel_data.get("type", "посилається"),
                            rel_data.get("description"),
                            rel_data.get("confidence", 100)
                        )
            
            self.db.commit()
        
        # Sync to Neo4j if not already synced
        neo4j_service.create_legal_act_node(
            act.id,
            act.nreg,
            act.title,
            act.subset_id
        )
        
        logger.info(f"Successfully processed act {nreg}")
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
        
        for name, count in categories_data:
            category = self.db.query(Category).filter(Category.name == name).first()
            if not category:
                category = Category(name=name, element_count=count)
                self.db.add(category)
            else:
                category.element_count = count
        
        self.db.commit()
        
        # Sync to Neo4j
        for category in self.db.query(Category).all():
            neo4j_service.create_category_node(
                category.id,
                category.name,
                category.element_count
            )
        
        logger.info("Categories initialized")


# Singleton instance will be created per request

