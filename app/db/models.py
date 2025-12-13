from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    experience_points = Column(Integer, default=0)
    level = Column(Integer, default=1)

    user_courses = relationship("UserCourse", backref="user")
    user_progress = relationship("UserProgress", backref="user")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    topic = Column(String, index=True)
    difficulty = Column(String)
    estimated_hours = Column(Float)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    sorting_method = Column(String, default="smart")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    modules = relationship("Module", backref="course")
    user_courses = relationship("UserCourse", backref="course")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String)
    order_index = Column(Integer)
    description = Column(Text)

    lessons = relationship("Lesson", backref="module")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    title = Column(String)
    order_index = Column(Integer)
    content_type = Column(String)
    content_url = Column(String)
    content_data = Column(JSON)
    description = Column(Text)
    duration_minutes = Column(Integer)
    estimated_difficulty = Column(String)

    user_progress = relationship("UserProgress", backref="lesson")


class UserCourse(Base):
    __tablename__ = "user_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    enrolled_at = Column(DateTime, default=datetime.now)
    completed = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    completed = Column(Boolean, default=False)
    watched_seconds = Column(Integer, default=0)
    last_watched = Column(DateTime, default=datetime.now)


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    message = Column(Text)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime, nullable=True)

    # Связи
    user = relationship("User", backref="notifications")
    course = relationship("Course", backref="notifications")
