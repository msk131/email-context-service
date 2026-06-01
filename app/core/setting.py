"""Application configuration (Pydantic BaseSettings).

Environment variables are read from .env file at runtime.
All settings are validated by Pydantic.
"""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # App metadata
    app_name: str = "Email Context API"
    app_env: str = Field(
        "local", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT")
    )

    # Database
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    database_pool_size: int = Field(10, ge=1, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(
        20, ge=0, validation_alias="DATABASE_MAX_OVERFLOW"
    )
    database_pool_timeout_seconds: int = Field(
        30, ge=1, validation_alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )
    database_pool_recycle_seconds: int = Field(
        1800, ge=1, validation_alias="DATABASE_POOL_RECYCLE_SECONDS"
    )

    # JWT authentication
    jwt_secret_key: str = Field(..., validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Cache
    summary_cache_ttl_seconds: int = Field(
        3600, validation_alias="SUMMARY_CACHE_TTL_SECONDS"
    )
    summary_cache_max_items: int = Field(
        512, validation_alias="SUMMARY_CACHE_MAX_ITEMS"
    )
    redis_url: str = Field("", validation_alias="REDIS_URL")
    search_cache_ttl_seconds: int = Field(
        300, ge=1, validation_alias="SEARCH_CACHE_TTL_SECONDS"
    )

    # HTTP security controls
    cors_allowed_origins: list[str] = Field(
        default_factory=list, validation_alias="CORS_ALLOWED_ORIGINS"
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["testserver", "localhost", "127.0.0.1", "*.local"],
        validation_alias="TRUSTED_HOSTS",
    )
    request_id_max_length: int = Field(
        128, ge=16, le=512, validation_alias="REQUEST_ID_MAX_LENGTH"
    )

    # LLM provider
    llm_api_key: str = Field(
        "", validation_alias=AliasChoices("LLM_API_KEY", "GEMINI_API_KEY")
    )
    llm_model: str = Field(
        "gemini-2.5-flash", validation_alias=AliasChoices("LLM_MODEL", "GEMINI_MODEL")
    )

    # Vector search / retrieval
    vectorizer_enabled: bool = Field(True, validation_alias="VECTORIZER_ENABLED")
    vectorizer_cache_enabled: bool = Field(
        True, validation_alias="VECTORIZER_CACHE_ENABLED"
    )
    vectorizer_min_relevance_score: float = Field(
        0.0, ge=0.0, validation_alias="VECTORIZER_MIN_RELEVANCE_SCORE"
    )
    azure_ai_search_endpoint: str = Field(
        "", validation_alias="AZURE_AI_SEARCH_ENDPOINT"
    )
    azure_ai_search_api_key: str = Field("", validation_alias="AZURE_AI_SEARCH_API_KEY")
    azure_ai_search_index_name: str = Field(
        "", validation_alias="AZURE_AI_SEARCH_INDEX_NAME"
    )
    azure_ai_search_api_version: str = Field(
        "2024-07-01", validation_alias="AZURE_AI_SEARCH_API_VERSION"
    )
    azure_ai_search_semantic_configuration: str = Field(
        "", validation_alias="AZURE_AI_SEARCH_SEMANTIC_CONFIGURATION"
    )
    azure_ai_search_content_vector_field: str = Field(
        "contentVector", validation_alias="AZURE_AI_SEARCH_CONTENT_VECTOR_FIELD"
    )
    pgvector_enabled: bool = Field(True, validation_alias="PGVECTOR_ENABLED")
    pgvector_embedding_dimensions: int = Field(
        384, ge=1, validation_alias="PGVECTOR_EMBEDDING_DIMENSIONS"
    )

    # Encryption
    encryption_key_hex: str = Field(..., validation_alias="ENCRYPTION_KEY_HEX")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("cors_allowed_origins", "trusted_hosts", mode="before")
    @classmethod
    def split_csv_settings(cls, value):
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def reject_wildcard_credentialed_cors(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS cannot contain '*' because credentialed CORS is enabled"
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env in {"prod", "production"}


settings = Settings()
