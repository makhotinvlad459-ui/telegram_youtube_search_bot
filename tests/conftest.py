import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.database import Base


@pytest.fixture
def test_settings():
    return Settings(
        TELEGRAM_BOT_TOKEN="test_token",
        YOUTUBE_API_KEY="test_key",
        DATABASE_URL="sqlite:///:memory:",
    )


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    yield db

    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def setup_factory_session(test_db):
    """Автоматически устанавливает сессию для всех фабрик"""
    from factories import UserFactory

    UserFactory._meta.sqlalchemy_session = test_db
    yield
    UserFactory._meta.sqlalchemy_session = None
