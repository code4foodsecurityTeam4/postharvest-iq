from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    AT_API_KEY: Optional[str] = None
    AT_USERNAME: Optional[str] = None
    SECRET_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()