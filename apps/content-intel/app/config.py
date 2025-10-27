"""Configuration helpers for environment variables and secret loading."""

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Service level configuration driven by environment variables."""

    version: str = Field(default="0.1.0", alias="AIO_CONTENT_INTEL_VERSION")
    environment: str = Field(default="development", alias="AIO_ENV")
    default_locale: str = Field(default="id_ID", alias="DEFAULT_LOCALE")
    fallback_country: str = Field(default="ID", alias="FALLBACK_COUNTRY")

    # LLM providers
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")

    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openrouter/auto", alias="OPENROUTER_MODEL")

    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    llama_endpoint: Optional[str] = Field(default=None, alias="LLAMA_ENDPOINT")
    llama_model: str = Field(default="meta-llama/Meta-Llama-3-8B-Instruct", alias="LLAMA_MODEL")

    llm_timeout_seconds: int = Field(default=45, alias="LLM_TIMEOUT_SECONDS")
    llm_temperature: float = Field(default=0.5, alias="LLM_TEMPERATURE")

    # Search providers
    serp_google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_API_KEY")
    serp_google_cx: Optional[str] = Field(default=None, alias="GOOGLE_SEARCH_CX")
    bing_api_key: Optional[str] = Field(default=None, alias="BING_SEARCH_API_KEY")
    serper_api_key: Optional[str] = Field(default=None, alias="SERPER_API_KEY")

    # Trend providers
    google_trends_username: Optional[str] = Field(default=None, alias="GOOGLE_TRENDS_USERNAME")
    google_trends_password: Optional[str] = Field(default=None, alias="GOOGLE_TRENDS_PASSWORD")

    # Media providers
    pexels_api_key: Optional[str] = Field(default=None, alias="PEXELS_API_KEY")
    pixabay_api_key: Optional[str] = Field(default=None, alias="PIXABAY_API_KEY")
    ai_image_endpoint: Optional[str] = Field(default=None, alias="AI_IMAGE_ENDPOINT")
    ai_image_api_key: Optional[str] = Field(default=None, alias="AI_IMAGE_API_KEY")

    # Persistence & caching
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    history_retention_days: int = Field(default=60, alias="HISTORY_RETENTION_DAYS")
    sitemap_cache_ttl: int = Field(default=3600, alias="SITEMAP_CACHE_TTL")

    # Notifications
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    alert_email: Optional[str] = Field(default=None, alias="ALERT_EMAIL")
    email_sender: Optional[str] = Field(default=None, alias="EMAIL_SENDER")

    autopublish_default: str = Field(default="manual", alias="AUTOPUBLISH_DEFAULT")
    activity_log_console: bool = Field(default=True, alias="ACTIVITY_LOG_CONSOLE")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()  # type: ignore[arg-type]


settings = get_settings()
