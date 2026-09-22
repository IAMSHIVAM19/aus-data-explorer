"""
Centralized Application Configuration
Uses pydantic-settings for validated, type-safe configuration management.
All environment variables are loaded and validated once at startup.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # OpenRouter LLM Configuration
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct",
        alias="OPENROUTER_MODEL"
    )

    # Database
    db_path: str = Field(
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "data/aus_labour_force.db"))
    )

    # Query Execution Limits
    query_timeout_seconds: float = 3.0
    max_reflection_retries: int = 2
    max_row_limit: int = 1000

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance — import this throughout the app
settings = Settings()
