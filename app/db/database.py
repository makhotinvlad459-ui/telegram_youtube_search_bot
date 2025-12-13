from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Создаем движок SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    ),
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def init_db():
    """Инициализировать базу данных - создать все таблицы"""
    print("🗄️ Создание таблиц базы данных...")
    from app.db.models import (
        Course,
        Lesson,
        Module,
        User,
        UserCourse,
        UserNotification,
        UserProgress,
    )

    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")


def get_db():
    """Получить сессию базы данных (для зависимостей)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
