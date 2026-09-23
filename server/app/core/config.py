"""
FastAPI Configuration - Jubi Multi-Agent Harness API

This module uses Pydantic BaseSettings for environment variable loading.
Follows 12-factor app principles with config stored in .env files.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Jubi Multi-Agent Harness"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Ollama Model Configuration
    OLLAMA_MODEL: str = "qwen3.5:9b"
    OLLAMA_TEMPERATURE: float = 0.0
    OLLAMA_NUM_CTX: int = 16384
    OLLAMA_KEEP_ALIVE: str = "5m"
    OLLAMA_BASE_URL: str = "http://192.168.1.6:11434"
    
    # Sandbox Configuration
    SANDBOX_ROOT: str = "/tmp/jubi-sandbox/"
    MAX_SANDBOX_SIZE_MB: int = 100
    
    # API Configuration
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 2024
    CORS_ORIGINS: str = "*"  # Comma-separated list (use * for testing)
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create global settings instance
settings = Settings()
