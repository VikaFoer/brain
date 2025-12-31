"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Rada API
    RADA_API_TOKEN: Optional[str] = None
    RADA_API_BASE_URL: str = "https://data.rada.gov.ua"
    RADA_API_RATE_LIMIT: int = 60  # запитів на хвилину
    RADA_API_DELAY: float = 6.0  # секунд між запитами
    
    # PostgreSQL
    DATABASE_URL: str
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    
    # Application
    APP_NAME: str = "Legal Graph System"
    DEBUG: bool = True
    SECRET_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

