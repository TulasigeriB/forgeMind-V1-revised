from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "ForgeMind"
    API_V1_STR: str = "/api/v1"
    
    # DB Defaults for local dev (Docker)
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/forgemind"
    
    SECRET_KEY: str = "FORGEMIND_DEV_SECRET_KEY_CHANGE_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
