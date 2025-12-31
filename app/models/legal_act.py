"""
Legal Act models - represents elements (елементи множини)
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class LegalAct(Base):
    """Legal Act (Елемент множини) - individual legal document"""
    __tablename__ = "legal_acts"
    
    id = Column(Integer, primary_key=True, index=True)
    nreg = Column(String(100), nullable=False, unique=True, index=True)  # Номер реєстрації
    title = Column(String(1000), nullable=False)
    text = Column(Text, nullable=True)  # Повний текст документа
    text_json = Column(JSON, nullable=True)  # Структурований JSON з API
    card_json = Column(JSON, nullable=True)  # Картка документа
    
    # Metadata
    document_type = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)  # діє, втратив чинність, тощо
    date_acceptance = Column(DateTime(timezone=True), nullable=True)
    date_publication = Column(DateTime(timezone=True), nullable=True)
    
    # Processing flags
    is_processed = Column(Boolean, default=False)  # Чи оброблено для виділення елементів
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    subset_id = Column(Integer, ForeignKey("subsets.id"), nullable=True)
    subset = relationship("Subset", back_populates="legal_acts")
    
    categories = relationship("ActCategory", back_populates="legal_act", cascade="all, delete-orphan")
    relations = relationship("ActRelation", foreign_keys="ActRelation.source_act_id", back_populates="source_act")
    inverse_relations = relationship("ActRelation", foreign_keys="ActRelation.target_act_id", back_populates="target_act")
    
    # Extracted elements (from OpenAI processing)
    extracted_elements = Column(JSON, nullable=True)  # Виділені елементи множини
    extracted_relations = Column(JSON, nullable=True)  # Виявлені зв'язки
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<LegalAct(id={self.id}, nreg='{self.nreg}', title='{self.title[:50]}...')>"


class ActCategory(Base):
    """Many-to-many relationship between acts and categories"""
    __tablename__ = "act_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    act_id = Column(Integer, ForeignKey("legal_acts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    confidence = Column(Integer, default=100)  # Від 0 до 100
    
    # Relationships
    legal_act = relationship("LegalAct", back_populates="categories")
    category = relationship("Category", back_populates="act_categories")
    
    def __repr__(self):
        return f"<ActCategory(act_id={self.act_id}, category_id={self.category_id})>"


class ActRelation(Base):
    """Relations between legal acts (відношення між множинами)"""
    __tablename__ = "act_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    source_act_id = Column(Integer, ForeignKey("legal_acts.id"), nullable=False)
    target_act_id = Column(Integer, ForeignKey("legal_acts.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)  # посилається, змінює, скасовує, тощо
    description = Column(Text, nullable=True)
    confidence = Column(Integer, default=100)
    
    # Relationships
    source_act = relationship("LegalAct", foreign_keys=[source_act_id], back_populates="relations")
    target_act = relationship("LegalAct", foreign_keys=[target_act_id], back_populates="inverse_relations")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ActRelation(source={self.source_act_id}, target={self.target_act_id}, type='{self.relation_type}')>"

