import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.db.models import Course, Lesson, Module, User


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    telegram_id = factory.Sequence(lambda n: 100000 + n)
    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    experience_points = 0
    level = 1
