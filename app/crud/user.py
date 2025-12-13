from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import User, UserCourse, UserProgress


def get_or_create_user(db: Session, user_data: dict) -> User:
    """Получить или создать пользователя"""
    user = db.query(User).filter(User.telegram_id == user_data["telegram_id"]).first()

    if not user:
        user = User(
            telegram_id=user_data["telegram_id"],
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            created_at=datetime.utcnow(),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def update_user_experience(db: Session, user_id: int, points: int) -> User:
    """Добавить опыт пользователю"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    user.experience_points += points

    # Обновляем уровень (каждые 100 опыта = 1 уровень)
    new_level = user.experience_points // 100 + 1
    if new_level > user.level:
        user.level = new_level

    db.commit()
    db.refresh(user)
    return user


def get_user_stats(db: Session, user_id: int) -> Dict:
    """Получить статистику пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return {}

    # Получаем курсы пользователя
    user_courses = db.query(UserCourse).filter(UserCourse.user_id == user_id).all()

    # Получаем прогресс
    progress_records = (
        db.query(UserProgress).filter(UserProgress.user_id == user_id).all()
    )

    # Статистика
    total_courses = len(user_courses)
    completed_courses = sum(1 for uc in user_courses if uc.completed)
    completed_lessons = sum(1 for p in progress_records if p.completed)
    total_time_watched = sum(p.watched_seconds for p in progress_records)

    # Активность (курсы за последние 7 дней)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_courses = sum(
        1 for uc in user_courses if uc.enrolled_at and uc.enrolled_at >= seven_days_ago
    )

    # Опыт и уровень
    experience_points = (
        completed_courses * 50  # 50 опыта за завершённый курс
        + completed_lessons * 5  # 5 опыта за урок
        + total_time_watched // 60  # 1 опыт за минуту просмотра
    )

    level = 1 + (experience_points // 100)  # Каждые 100 опыта - уровень

    # Процент завершения
    completion_rate = (
        (completed_courses / total_courses * 100) if total_courses > 0 else 0
    )

    return {
        "experience_points": experience_points,
        "level": level,
        "total_courses": total_courses,
        "completed_courses": completed_courses,
        "completed_lessons": completed_lessons,
        "total_time_watched_minutes": total_time_watched // 60,
        "recent_courses_7_days": recent_courses,
        "completion_rate": completion_rate,
        "user_id": user_id,
        "username": user.username,
        "first_name": user.first_name,
    }


def get_top_users(db: Session, limit: int = 10) -> List[Dict]:
    """Получить топ пользователей по опыту"""
    users = db.query(User).order_by(User.experience_points.desc()).limit(limit).all()

    return [
        {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "experience_points": user.experience_points,
            "level": user.level,
            "courses_count": len(user.courses),
        }
        for user in users
    ]


def mark_lesson_completed(
    db: Session, user_id: int, lesson_id: int, watched_seconds: int = 0
) -> UserProgress:
    """Отметить урок как пройденный"""
    # Проверяем, есть ли уже прогресс
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.lesson_id == lesson_id)
        .first()
    )

    if progress:
        # Обновляем существующий прогресс
        progress.completed = True
        progress.watched_seconds = watched_seconds
        progress.last_watched = datetime.utcnow()
    else:
        # Создаем новый прогресс
        progress = UserProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            completed=True,
            watched_seconds=watched_seconds,
            last_watched=datetime.utcnow(),
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return progress


def update_watch_time(
    db: Session, user_id: int, lesson_id: int, watched_seconds: int
) -> UserProgress:
    """Обновить время просмотра урока"""
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.lesson_id == lesson_id)
        .first()
    )

    if not progress:
        progress = UserProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            completed=False,
            watched_seconds=watched_seconds,
            last_watched=datetime.utcnow(),
        )
        db.add(progress)
    else:
        progress.watched_seconds = watched_seconds
        progress.last_watched = datetime.utcnow()

    db.commit()
    db.refresh(progress)
    return progress
