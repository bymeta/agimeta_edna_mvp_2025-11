"""Configuration management using Pydantic Settings"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "postgresql://edna:edna@localhost:5433/edna"
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

