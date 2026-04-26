from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rxexplainer"
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = "./chroma_db"
    log_level: str = "INFO"
    drugbank_api_key: str = ""
    google_tts_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
