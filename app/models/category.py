"""
Category model - represents a set (множина)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Category(Base):
    """Category (Множина) - top level category"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, unique=True, index=True)
    code = Column(Integer, nullable=True, index=True)  # Код класифікації (номер категорії)
    description = Column(Text, nullable=True)
    element_count = Column(Integer, default=0)  # Кількість елементів множини
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subsets = relationship("Subset", back_populates="category", cascade="all, delete-orphan")
    act_categories = relationship("ActCategory", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', elements={self.element_count})>"

