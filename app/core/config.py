from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Elevator Escalator AI API"
    env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///C:/Users/Andhias/services/api/local_dev.db"

    # Connection pool (PostgreSQL only)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # LLM provider: openai | anthropic | gemini | openai_compatible
    llm_provider: str = "openai_compatible"
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    # OpenAI compatible (Ollama, OpenRouter, etc.)
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()