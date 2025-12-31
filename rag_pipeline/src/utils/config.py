"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_EMBED_MODEL: str = "text-embedding-3-large"
    OPENAI_EMBED_DIMENSIONS: int = 3072
    
    # Database
    DATABASE_URL: str
    
    # Chunking
    CHUNK_SIZE: int = 8000  # tokens
    CHUNK_OVERLAP: float = 0.15  # 15%
    
    # Embeddings
    BATCH_SIZE: int = 100
    MAX_RETRIES: int = 3
    RATE_LIMIT_RPM: int = 60
    
    # Retrieval
    TOPK: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Processing
    MAX_WORKERS: int = 4
    NEEDS_OCR_THRESHOLD: float = 0.1  # Якщо <10% тексту - вважаємо сканом
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

