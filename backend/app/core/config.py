from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "paperlens-backend"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/paperlens"
    CORS_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str = "paperlens_secret_key_change_in_production_secure_789456123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
    UPLOAD_DIR: str = "storage/uploads"
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_BATCH_SIZE: int = 64
    RETRIEVAL_SEMANTIC_WEIGHT: float = 0.60
    RETRIEVAL_SECTION_WEIGHT: float = 0.25
    RETRIEVAL_KEYWORD_WEIGHT: float = 0.15
    MAX_EVIDENCE_CONTEXT_TOKENS: int = 1500
    DEDUPLICATION_SIMILARITY_THRESHOLD: float = 0.85
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0
    MIN_SUPPORT_SCORE_THRESHOLD: float = 0.70

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
