"""Configuration helpers for environment variables and secret loading."""

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Service level configuration driven by environment variables."""

    version: str = Field(default="0.1.0", alias="AIO_CONTENT_INTEL_VERSION")
    environment: str = Field(default="development", alias="AIO_ENV")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    llama_endpoint: Optional[str] = Field(default=None, alias="LLAMA_ENDPOINT")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()  # type: ignore[arg-type]


settings = get_settings()
