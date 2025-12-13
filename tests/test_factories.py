import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factories import UserFactory  # импортируем фабрику

from app.db.models import User


def test_user_factory(test_db):
    UserFactory._meta.sqlalchemy_session = test_db
    user = UserFactory()

    assert user.telegram_id >= 100000
    assert user.username is not None
    assert user.experience_points == 0
    assert user.level == 1

    user_from_db = test_db.query(User).filter_by(telegram_id=user.telegram_id).first()
    assert user_from_db is not None
