from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OSDH_ENV: str = "development"
    OSDH_HOST: str = "0.0.0.0"
    OSDH_PORT: int = 8080
    OSDH_DB_PATH: str = "./data/osdh.db"
    OSDH_SNAPSHOT_DIR: str = "./data/snapshots"
    OSDH_CACHE_DIR: str = "./data/cache"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"
    OLLAMA_TIMEOUT: int = 120

    GITHUB_API_TOKEN: str = ""
    GITHUB_RATE_LIMIT_DELAY: float = 2.0

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
