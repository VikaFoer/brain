from app.models.category import Category
from app.models.legal_act import LegalAct, ActCategory, ActRelation
from app.models.subset import Subset

# Import all models to ensure they're registered with Base
__all__ = ["Category", "LegalAct", "ActCategory", "ActRelation", "Subset"]

