import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factories import UserFactory

from app.crud.user import get_or_create_user, get_user_by_telegram_id, get_user_stats


def test_get_or_create_user_new(test_db):
    """Тест создания нового пользователя"""
    user_data = {
        "telegram_id": 999999,
        "username": "new_user",
        "first_name": "New",
        "last_name": "User",
    }

    user = get_or_create_user(test_db, user_data)

    assert user.telegram_id == 999999
    assert user.username == "new_user"
    assert user.experience_points == 0
    assert user.level == 1


def test_get_or_create_user_existing(test_db):
    """Тест получения существующего пользователя"""
    # Создаём через фабрику
    factory_user = UserFactory()
    test_db.commit()

    user_data = {
        "telegram_id": factory_user.telegram_id,
        "username": "updated_username",
        "first_name": factory_user.first_name,
    }

    # Должен вернуть существующего пользователя
    user = get_or_create_user(test_db, user_data)

    assert user.id == factory_user.id
    assert user.telegram_id == factory_user.telegram_id
    assert user.username == factory_user.username


def test_get_user_by_telegram_id(test_db):
    """Тест поиска по telegram_id"""
    factory_user = UserFactory()
    test_db.commit()

    user = get_user_by_telegram_id(test_db, factory_user.telegram_id)

    assert user is not None
    assert user.id == factory_user.id
    assert user.telegram_id == factory_user.telegram_id


def test_get_user_stats(test_db):
    """Тест статистики пользователя"""
    user = UserFactory()
    test_db.commit()

    stats = get_user_stats(test_db, user.id)

    assert "experience_points" in stats
    assert "level" in stats
    assert "total_courses" in stats
    assert stats["experience_points"] == 0
    assert stats["level"] == 1
