"""Application configuration (Pydantic BaseSettings).

Environment variables are read from .env file at runtime.
All settings are validated by Pydantic.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # App metadata
    app_name: str = "Email Context API"
    
    # Database
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    
    # JWT authentication
    jwt_secret_key: str = Field(..., validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Cache
    summary_cache_ttl_seconds: int = Field(3600, validation_alias="SUMMARY_CACHE_TTL_SECONDS")
    summary_cache_max_items: int = Field(512, validation_alias="SUMMARY_CACHE_MAX_ITEMS")

    # LLM provider
    gemini_api_key: str = Field("", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-1.5-flash", validation_alias="GEMINI_MODEL")

    # Encryption
    encryption_key_hex: str = Field(..., validation_alias="ENCRYPTION_KEY_HEX")

    # Updated configuration format for Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
