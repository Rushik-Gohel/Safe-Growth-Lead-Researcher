"""Configuration management for the Safe-Growth Lead Researcher."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Keys
    google_api_key: str = Field(..., description="Google Gemini API key")
    tavily_api_key: str = Field(..., description="Tavily Search API key")
    langchain_api_key: Optional[str] = Field(None, description="LangSmith API key")
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(default=True, description="Enable LangSmith tracing")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com")
    langchain_project: str = Field(default="safe-growth-researcher")
    
    # Rate Limits - Gemini 1.5 Flash (Tier 1)
    gemini_rpm: int = Field(default=15, description="Requests per minute")
    gemini_tpm: int = Field(default=1_000_000, description="Tokens per minute")
    gemini_tpd: int = Field(default=1500, description="Tokens per day")
    
    # Tavily Rate Limits
    tavily_monthly_limit: int = Field(default=1000, description="Monthly search limit")
    
    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable metrics tracking")
    enable_tracing: bool = Field(default=True, description="Enable execution tracing")
    
    # Security
    max_input_length: int = Field(default=1000, description="Maximum input length")
    enable_guardrails: bool = Field(default=True, description="Enable security guardrails")
    
    # Performance & Caching
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=3600, description="Default cache TTL in seconds (1 hour)")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    
    # Cache TTL overrides for specific operations
    workflow_cache_ttl: int = Field(default=3600, description="Workflow result cache TTL (1 hour)")
    linkedin_cache_ttl: int = Field(default=3600, description="LinkedIn profile cache TTL (1 hour)")
    search_cache_ttl: int = Field(default=1800, description="Search results cache TTL (30 minutes)")
    company_news_cache_ttl: int = Field(default=3600, description="Company news cache TTL (1 hour)")
    industry_trends_cache_ttl: int = Field(default=7200, description="Industry trends cache TTL (2 hours)")
    
    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=2, description="Initial retry delay in seconds")
    
    # Model Configuration
    model_name: str = Field(default="models/gemini-2.5-flash", description="Gemini model name")
    temperature: float = Field(default=0.7, description="LLM temperature")
    max_output_tokens: int = Field(default=2048, description="Maximum output tokens")
    
    def setup_langsmith(self) -> None:
        """Configure LangSmith environment variables."""
        if self.enable_tracing and self.langchain_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = str(self.langchain_tracing_v2)
            os.environ["LANGCHAIN_ENDPOINT"] = self.langchain_endpoint
            os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project


# Global settings instance
settings = Settings()

# Setup LangSmith on import
settings.setup_langsmith()


