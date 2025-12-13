from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.db.models import Course, Module, UserCourse, UserProgress


def create_course(
    db: Session, course_data: dict, user_id: Optional[int] = None
) -> Course:
    """Создать новый курс"""
    course = Course(
        title=course_data["title"],
        description=course_data.get("description", ""),
        topic=course_data["topic"],
        difficulty=course_data.get("difficulty", "beginner"),
        estimated_hours=course_data.get("estimated_hours", 0),
        is_public=course_data.get("is_public", True),
        created_at=datetime.utcnow(),
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    # Если указан пользователь - добавляем его на курс
    if user_id:
        enroll_user_to_course(db, user_id, course.id)

    return course


def get_course_by_id(db: Session, course_id: int) -> Optional[Course]:
    """Получить курс по ID со всеми зависимостями"""
    return (
        db.query(Course)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .filter(Course.id == course_id)
        .first()
    )


def get_courses_by_topic(db: Session, topic: str, limit: int = 20) -> List[Course]:
    """Получить курсы по теме"""
    return (
        db.query(Course)
        .filter(Course.topic.ilike(f"%{topic}%"), Course.is_public )
        .order_by(desc(Course.created_at))
        .limit(limit)
        .all()
    )


def get_popular_courses(db: Session, limit: int = 10) -> List[Course]:
    """Получить популярные курсы (по количеству записей)"""
    return (
        db.query(Course)
        .outerjoin(UserCourse)
        .filter(Course.is_public )
        .group_by(Course.id)
        .order_by(func.count(UserCourse.id).desc())
        .limit(limit)
        .all()
    )


def search_courses(db: Session, query: str, limit: int = 20) -> List[Course]:
    """Поиск курсов по названию и описанию"""
    return (
        db.query(Course)
        .filter(
            and_(
                Course.is_public ,
                or_(
                    Course.title.ilike(f"%{query}%"),
                    Course.description.ilike(f"%{query}%"),
                    Course.topic.ilike(f"%{query}%"),
                ),
            )
        )
        .order_by(desc(Course.created_at))
        .limit(limit)
        .all()
    )


def enroll_user_to_course(db: Session, user_id: int, course_id: int) -> UserCourse:
    """Записать пользователя на курс"""
    # Проверяем, не записан ли уже
    existing = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
        .first()
    )

    if existing:
        return existing

    user_course = UserCourse(
        user_id=user_id, course_id=course_id, enrolled_at=datetime.now()
    )

    db.add(user_course)
    db.commit()
    db.refresh(user_course)
    return user_course


def get_user_courses(db: Session, user_id: int) -> List[Tuple[Course, UserCourse]]:
    """Получить курсы пользователя с информацией о прогрессе"""
    user_courses = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id)
        .options(
            joinedload(UserCourse.course)
            .joinedload(Course.modules)
            .joinedload(Module.lessons)
        )
        .all()
    )

    return [(uc.course, uc) for uc in user_courses]


def update_course_progress(db: Session, user_id: int, course_id: int) -> UserCourse:
    """Обновить прогресс прохождения курса"""
    from .user import update_user_experience

    user_course = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.course_id == course_id)
        .first()
    )

    if not user_course:
        return None

    # Получаем все уроки курса
    course = get_course_by_id(db, course_id)
    if not course:
        return user_course

    total_lessons = sum(len(module.lessons) for module in course.modules)
    if total_lessons == 0:
        return user_course

    # Считаем пройденные уроки
    completed_lessons = (
        db.query(UserProgress)
        .filter(
            UserProgress.user_id == user_id,
            UserProgress.completed ,
            UserProgress.lesson_id.in_(
                [lesson.id for module in course.modules for lesson in module.lessons]
            ),
        )
        .count()
    )

    # Обновляем процент завершения
    completion_percentage = (completed_lessons / total_lessons) * 100
    user_course.completion_percentage = completion_percentage

    # Если все уроки пройдены - отмечаем курс как завершенный
    if completion_percentage >= 100 and not user_course.completed:
        user_course.completed = True
        # Добавляем опыт за завершение курса
        update_user_experience(db, user_id, 50)  # 50 опыта за курс

    db.commit()
    db.refresh(user_course)
    return user_course


def get_course_statistics(db: Session, course_id: int) -> Dict:
    """Получить статистику курса"""
    course = get_course_by_id(db, course_id)
    if not course:
        return {}

    # Количество записей
    enrollments = db.query(UserCourse).filter(UserCourse.course_id == course_id).count()

    # Количество завершивших
    completed = (
        db.query(UserCourse)
        .filter(UserCourse.course_id == course_id, UserCourse.completed )
        .count()
    )

    # Средний процент завершения
    avg_completion = (
        db.query(func.avg(UserCourse.completion_percentage))
        .filter(UserCourse.course_id == course_id)
        .scalar()
        or 0
    )

    return {
        "course_id": course_id,
        "title": course.title,
        "enrollments": enrollments,
        "completed": completed,
        "completion_rate": (completed / enrollments * 100) if enrollments > 0 else 0,
        "average_completion": round(avg_completion, 1),
        "modules_count": len(course.modules),
        "lessons_count": sum(len(m.lessons) for m in course.modules),
        "estimated_hours": course.estimated_hours,
    }


def get_user_progress_for_course(db: Session, user_id: int, course_id: int) -> Dict:
    """Получить прогресс пользователя по курсу"""
    # Получаем курс
    course = get_course_by_id(db, course_id)
    if not course:
        return {}

    # Собираем информацию о прогрессе
    course_progress = []
    total_lessons = 0
    completed_lessons = 0
    total_watch_time = 0

    for module in course.modules:
        module_progress = {"module_id": module.id, "title": module.title, "lessons": []}

        for lesson in module.lessons:
            total_lessons += 1

            # Получаем прогресс по уроку
            progress = (
                db.query(UserProgress)
                .filter(
                    UserProgress.user_id == user_id, UserProgress.lesson_id == lesson.id
                )
                .first()
            )

            completed = False
            watched_seconds = 0
            if progress:  # Проверяем, что progress не None
                completed = progress.completed
                watched_seconds = progress.watched_seconds

            lesson_info = {
                "lesson_id": lesson.id,
                "title": lesson.title,
                "duration_minutes": lesson.duration_minutes,
                "completed": completed,
                "watched_seconds": watched_seconds,
            }

            module_progress["lessons"].append(lesson_info)

            if completed:
                completed_lessons += 1
                total_watch_time += watched_seconds

        course_progress.append(module_progress)

    completion_percentage = (
        (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    )

    return {
        "course_id": course_id,
        "course_title": course.title,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "completion_percentage": round(completion_percentage, 1),
        "total_watch_time_minutes": total_watch_time // 60,
        "modules": course_progress,
    }


def create_course_for_user(db: Session, course_data: dict, user_id: int) -> Course:
    """Создать курс для конкретного пользователя"""
    course = Course(
        title=course_data["title"],
        description=course_data.get("description", ""),
        topic=course_data["topic"],
        difficulty=course_data.get("difficulty", "beginner"),
        estimated_hours=course_data.get("estimated_hours", 0),
        created_by=user_id,  # Устанавливаем владельца
        is_public=False,  # Приватный по умолчанию
        created_at=datetime.utcnow(),
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    # Автоматически записываем пользователя на курс
    enroll_user_to_course(db, user_id, course.id)

    return course


def get_user_created_courses(db: Session, user_id: int) -> List[Course]:
    """Получить курсы, созданные пользователем"""
    return (
        db.query(Course)
        .filter(Course.created_by == user_id)
        .options(joinedload(Course.modules).joinedload(Module.lessons))
        .order_by(desc(Course.created_at))
        .all()
    )


def get_courses_for_user(db: Session, user_id: int) -> List[Tuple[Course, UserCourse]]:
    """Получить все курсы пользователя (созданные + записанные)"""
    # Курсы, созданные пользователем
    created_courses = get_user_created_courses(db, user_id)

    # Курсы, на которые пользователь записан
    user_courses_list = get_user_courses(db, user_id)

    # Объединяем
    all_courses = []

    # Добавляем созданные курсы
    for course in created_courses:
        # Находим запись UserCourse если есть
        user_course = next(
            (uc for uc, _ in user_courses_list if uc.course_id == course.id), None
        )
        all_courses.append((course, user_course))

    # Добавляем курсы, на которые записан (но не создавал)
    for course, user_course in user_courses_list:
        if course.created_by != user_id:
            all_courses.append((course, user_course))

    return all_courses
