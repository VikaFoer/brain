"""
Subset model - represents a subset (підмножина)
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Subset(Base):
    """Subset (Підмножина) - subset of a category"""
    __tablename__ = "subsets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    element_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    category = relationship("Category", back_populates="subsets")
    legal_acts = relationship("LegalAct", back_populates="subset")
    
    def __repr__(self):
        return f"<Subset(id={self.id}, name='{self.name}', category_id={self.category_id})>"

