from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "ForgeMind"
    API_V1_STR: str = "/api/v1"

    # Updated to use the Psycopg 3 driver and localhost (for running locally outside Docker)
    DATABASE_URL: str = "postgresql+psycopg://postgres:adminforgemind@localhost:5432/forgemind_db"

    SECRET_KEY: str = "FORGEMIND_DEV_SECRET_KEY_CHANGE_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    AUTH_DISABLED_FOR_TESTING: bool = False
    TESSERACT_CMD: str = "tesseract"

    UPLOAD_DIR: str = str(BACKEND_DIR / "uploads")

    # Celery Configuration
    # redis://localhost:6379/0 means use Redis on localhost, database 0
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()