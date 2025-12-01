"""Configuration management using Pydantic Settings"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    # Default aligns with docker-compose Postgres settings:
    #   user: postgres, password: postgres, db: postgres, host: localhost:5433
    database_url: str = "postgresql://postgres:postgres@localhost:5433/postgres"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # API Gateway
    api_gateway_host: str = "0.0.0.0"
    api_gateway_port: int = 8000

    # Scanner
    scanner_batch_size: int = 1000

    # Pydantic v2 config: load from .env and ignore extra env vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

