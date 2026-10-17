"""Environment-based configuration without implicit .env loading."""
from functools import lru_cache
import os


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://forgemind:forgemind_dev_password@127.0.0.1:5432/forgemind_v1",
        )
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if origin.strip()
        ]


@lru_cache

def get_settings() -> Settings:
    return Settings()
