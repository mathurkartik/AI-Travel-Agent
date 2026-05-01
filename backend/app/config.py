"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # App
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    
    # LLM Provider (groq, openai, anthropic)
    llm_provider: str = "groq"
    
    # Groq Configuration (Default)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"  # Updated model (mixtral-8x7b-32768 was decommissioned)
    groq_max_tokens_per_request: int = 4000
    groq_temperature: float = 0.1  # Low for structured extraction
    
    # OpenAI (Fallback)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # Anthropic (Fallback)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # Token Budget Management (Groq = 100k tokens/day)
    enable_token_tracking: bool = True
    max_tokens_per_plan_request: int = 15000  # Safety limit per travel plan
    token_buffer_percent: int = 20  # Keep 20% buffer for daily limit
    
    # Agents
    agent_timeout_seconds: int = 30
    max_review_retries: int = 3
    
    # Caching to reduce token usage
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Tools (stubs for now)
    enable_web_search: bool = False
    enable_geo_routing: bool = False
    enable_pricing_api: bool = False
    enable_fx_api: bool = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
