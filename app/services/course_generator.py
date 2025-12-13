from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.models import Course, Lesson, Module
from app.services.youtube_service import YouTubeService

from .smart_sorter import SmartVideoSorter


class CourseGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.youtube = YouTubeService()
        self.sorter = SmartVideoSorter()

    def generate_course(
        self, topic: str, difficulty: str, user_id: int = None
    ) -> Course:
        """Генерация курса с умной сортировкой"""

        # 1. Поиск видео
        query = self._build_search_query(topic, difficulty)
        videos = self.youtube.search_videos(query, max_results=15)

        if not videos:
            raise ValueError(f"Не найдено видео по теме: {topic}")

        # 2. Умная сортировка
        sorted_videos = self.sorter.sort_videos(videos, topic, difficulty)

        # 3. Группировка в модули
        modules_videos = self.sorter.group_into_modules(sorted_videos, module_size=5)

        # 4. Создание структуры курса
        course = self._create_course_structure(
            topic, difficulty, modules_videos, user_id
        )

        return course

    def _build_search_query(self, topic: str, difficulty: str) -> str:
        """Формирует поисковый запрос"""
        difficulty_terms = {
            "beginner": "для начинающих основы обучение",
            "intermediate": "практика примеры разбор",
            "advanced": "продвинутый профессиональный эксперт",
        }

        terms = difficulty_terms.get(difficulty, "")
        return f"{topic} {terms} обучение урок"

    def _create_course_structure(
        self,
        topic: str,
        difficulty: str,
        modules_videos: List[List[Dict]],
        user_id: int = None,
        # <-- добавить user_id
    ) -> Course:
        """Создает структуру курса в БД"""

        # Создаем курс
        course = Course(
            title=f"Курс по {topic}",
            description=f"Умный курс по теме '{topic}' для уровня '{difficulty}'. "
            f"Автоматически сгенерирован и отсортирован от простого к сложному.",
            topic=topic,
            difficulty=difficulty,
            estimated_hours=sum(
                sum(v.get("duration", 600) for v in module) / 3600
                for module in modules_videos
            ),
            created_at=datetime.now(),
            sorting_method="smart",
            created_by=user_id,
            is_public=False if user_id else True,
        )

        self.db.add(course)
        self.db.flush()

        # Создаем модули и уроки
        for module_idx, module_videos in enumerate(modules_videos, 1):
            module_topic = module_videos[0].get("module_topic", f"Модуль {module_idx}")

            module = Module(
                course_id=course.id,
                title=f"Модуль {module_idx}: {module_topic}",
                order_index=module_idx,
                description=f"Модуль содержит {len(module_videos)} видеоуроков по теме {module_topic}",
            )

            self.db.add(module)
            self.db.flush()

            # Добавляем уроки
            for lesson_idx, video in enumerate(module_videos, 1):
                estimated_diff = video.get("estimated_difficulty", "intermediate")

                lesson = Lesson(
                    module_id=module.id,
                    title=video["title"],
                    order_index=lesson_idx,
                    content_type="video",
                    content_url=video["url"],
                    content_data={
                        "duration": video.get("duration"),
                        "views": video.get("view_count"),
                        "channel": video.get("channel"),
                        "thumbnail": video.get("thumbnail"),
                        "youtube_id": video.get("id"),
                    },
                    description=video.get("description", ""),
                    duration_minutes=video.get("duration", 600) // 60,
                    estimated_difficulty=estimated_diff,
                )
                self.db.add(lesson)

        self.db.commit()
        self.db.refresh(course)

        return course
