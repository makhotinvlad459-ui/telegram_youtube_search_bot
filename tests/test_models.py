from app.db.models import User


def test_user_model(test_db):
    """Тест создания пользователя в БД"""
    user = User(
        telegram_id=123456, username="testuser", first_name="Test", last_name="User"
    )

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    assert user.telegram_id == 123456
    assert user.experience_points == 0
    assert user.level == 1
    assert user.is_active is True
    assert user.created_at is not None
