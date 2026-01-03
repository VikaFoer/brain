"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"  # Latest stable model - GPT-4o (GPT-5.2-pro doesn't exist yet)
    OPENAI_CHAT_MODEL: str = "gpt-4o"  # Model specifically for chat (can be different from extraction)
    OPENAI_REASONING_EFFORT: str = "high"  # Reasoning effort: medium, high, very_high (for o1 models only)
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"  # Embeddings model
    OPENAI_EMBEDDING_DIMENSIONS: int = 3072  # Dimensions for text-embedding-3-large (default: 3072, can be 256, 1024, 3072)
    
    # OpenAI Token Limits (based on model capabilities and organization limits)
    # GPT-4o supports up to 16384 output tokens (max_tokens parameter)
    # Adjust these based on your organization's rate limits at: https://platform.openai.com/settings/organization/limits
    OPENAI_MAX_RESPONSE_TOKENS: int = 16384  # Max tokens for extraction tasks (GPT-4o limit: 16384)
    OPENAI_MAX_CHAT_TOKENS: int = 8192  # Max tokens for chat responses (can be up to 16384 for GPT-4o)
    
    # Weights & Biases (W&B) Configuration
    # Get your API key from: https://wandb.ai/settings
    WANDB_API_KEY: Optional[str] = None
    WANDB_PROJECT: str = "legal-graph-system"  # Project name in W&B
    WANDB_ENABLED: bool = True  # Enable/disable W&B logging
    WANDB_ENTITY: Optional[str] = None  # W&B entity/team name (optional)
    
    # Rada API
    RADA_API_TOKEN: Optional[str] = None
    RADA_API_BASE_URL: str = "https://data.rada.gov.ua"
    RADA_API_RATE_LIMIT: int = 60  # запитів на хвилину
    RADA_API_DELAY: float = 6.0  # секунд між запитами
    RADA_OPEN_DATA_DATASET_ID: Optional[str] = None  # ID набору даних з порталу відкритих даних (https://data.rada.gov.ua/open/data/)
    
    # PostgreSQL
    DATABASE_URL: Optional[str] = None
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None
    
    # Application
    APP_NAME: str = "Legal Graph System"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Railway автоматично інжектує змінні середовища, тому не потрібно env_file на Railway
        # Але залишаємо для локальної розробки


settings = Settings()

