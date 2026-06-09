from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "persistent-sales-assistant"
    environment: str = "dev"

    # DB
    database_url: str = "sqlite:///./app.db"

    # LLM (optional; app still runs without a key using deterministic fallback)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Catalog
    catalog_path: str = "catalog.json"

    # Eval thresholds
    confidence_flag_threshold: float = 0.55


settings = Settings()

