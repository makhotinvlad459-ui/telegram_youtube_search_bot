import asyncio
import logging
import time

from celery import current_task

from app.crud.course import enroll_user_to_course, get_course_by_id
from app.crud.user import get_user_by_id
from app.db.database import SessionLocal
from app.services.course_generator import CourseGenerator
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="generate_course_task")
def generate_course_task(
    self, topic: str, difficulty: str = "beginner", user_id: int = None
):
    """Фоновая задача генерации курса"""

    db = SessionLocal()
    try:
        # Шаг 1: Поиск видео
        self.update_state(
            state="PROGRESS",
            meta={"step": 1, "total": 3, "message": "🔍 Ищу видео на YouTube..."},
        )

        # Шаг 2: Анализ и сортировка
        self.update_state(
            state="PROGRESS",
            meta={
                "step": 2,
                "total": 3,
                "message": "📊 Анализирую и сортирую видео...",
            },
        )

        # Шаг 3: Создание курса
        self.update_state(
            state="PROGRESS",
            meta={"step": 3, "total": 3, "message": "🏗️ Создаю структуру курса..."},
        )

        generator = CourseGenerator(db)
        course = generator.generate_course(topic, difficulty, user_id)

        # Отправляем уведомление
        if user_id:
            send_course_ready_notification.delay(user_id, course.id)

        return {
            "status": "success",
            "course_id": course.id,
            "title": course.title,
            "modules": len(course.modules),
            "lessons": sum(len(m.lessons) for m in course.modules),
            "topic": topic,
            "difficulty": difficulty,
        }

    except Exception as e:
        logger.error(f"Failed to generate course: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="send_course_ready_notification")
def send_course_ready_notification(user_id: int, course_id: int):
    """Сохранить уведомление о готовности курса"""
    try:
        db = SessionLocal()
        try:
            # Получаем пользователя и курс
            from app.crud.course import enroll_user_to_course, get_course_by_id
            from app.crud.user import get_user_by_id

            user = get_user_by_id(db, user_id)
            course = get_course_by_id(db, course_id)

            if not user or not course:
                logger.error(f"User {user_id} or course {course_id} not found")
                return

            # Записываем пользователя на курс если еще не записан
            enroll_user_to_course(db, user.id, course_id)

            # Логируем вместо отправки сообщения
            logger.info(
                f"✅ КУРС ГОТОВ! User: {user_id}, Course: {course_id}, Title: {course.title}"
            )

            # Сохраняем в БД для отправки ботом позже
            from app.db.models import UserNotification

            notification = UserNotification(
                user_id=user_id,
                course_id=course_id,
                message=f"🎉 Курс готов: {course.title}",
            )
            db.add(notification)
            db.commit()

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to save notification: {e}")


@celery_app.task(bind=True, name="debug_task")
def debug_task(self):
    """Тестовая задача для проверки работы Celery"""
    return {
        "status": "success",
        "message": "Celery is working!",
        "timestamp": time.time(),
        "task_id": self.request.id,
        "worker": "learning_bot",
    }


@celery_app.task(name="test_task")
def test_task(message: str = "Hello"):
    """Простая тестовая задача"""
    return {
        "status": "success",
        "message": f"Test: {message}",
        "timestamp": time.time(),
    }


@celery_app.task(name="ping_task")
def ping_task():
    """Задача для проверки связи"""
    return {"status": "pong", "time": time.time()}


@celery_app.task(bind=True, name="long_task")
def long_task(self, seconds: int = 10):
    """Длительная задача с прогрессом"""
    for i in range(seconds):
        time.sleep(1)
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": seconds,
                "percent": int((i + 1) / seconds * 100),
                "message": f"Обработка... {i + 1}/{seconds}",
            },
        )
    return {"status": "completed", "seconds": seconds}


# Экспорт задач
__all__ = [
    "generate_course_task",
    "send_course_ready_notification",  # Добавил
    "debug_task",
    "test_task",
    "ping_task",
    "long_task",
]


@celery_app.task(name="send_course_ready_notification")
def send_course_ready_notification(user_id: int, course_id: int):
    """Сохранить уведомление о готовности курса"""
    try:
        db = SessionLocal()
        try:
            # Получаем пользователя и курс
            from app.crud.course import enroll_user_to_course, get_course_by_id
            from app.crud.user import get_user_by_id

            user = get_user_by_id(db, user_id)
            course = get_course_by_id(db, course_id)

            if not user or not course:
                logger.error(f"User {user_id} or course {course_id} not found")
                return

            # Записываем пользователя на курс если еще не записан
            enroll_user_to_course(db, user.id, course_id)

            # Логируем вместо отправки сообщения
            logger.info(
                f"✅ КУРС ГОТОВ! User: {user_id}, Course: {course_id}, Title: {course.title}"
            )

            # Сохраняем в БД
            from app.db.models import UserNotification

            notification = UserNotification(
                user_id=user_id,
                course_id=course_id,
                message=f"🎉 Курс готов: {course.title}",
            )
            db.add(notification)
            db.commit()
            logger.info(f"📨 Уведомление сохранено в БД: ID={notification.id}")

        except Exception as e:
            logger.error(f"Failed to save notification: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in notification task: {e}")
