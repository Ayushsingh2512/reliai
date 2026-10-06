from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql+asyncpg://reliai:password@localhost:5433/reliai"
    
    # Authentication
    jwt_secret_key: str = "dev-secret-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Timing variables from ADR-014
    detection_interval: int = 10
    prometheus_scrape_interval: str = "10s"
    correlation_window_seconds: int = 90
    dedup_window_seconds: int = 300
    experiment_reset_wait_seconds: int = 30
    experiment_observation_window: int = 600
    experiment_baseline_window: int = 60
    
    # LLM Provider (ADR-005)
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 30
    ai_mock_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
