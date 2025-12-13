from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    YOUTUBE_API_KEY: str

    DATABASE_URL: str = "sqlite:///./learning_bot.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    DEBUG: bool = True
    PROJECT_NAME: str = "Learning Bot"

    # Новое поле для админов
    ADMIN_USER_IDS: Optional[str] = None  # Или List[int] = []

    class Config:
        env_file = ".env"
        # Разрешаем дополнительные поля из .env
        extra = "allow"


settings = Settings()
