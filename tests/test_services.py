import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from factories import UserFactory

from app.db.models import Course, Lesson, Module
from app.services.course_generator import CourseGenerator
from app.services.youtube_service import YouTubeService


def test_course_generator_init(test_db):
    """Тест инициализации генератора курсов"""
    generator = CourseGenerator(test_db)
    assert generator.db == test_db
    assert isinstance(generator.youtube, YouTubeService)
    assert generator.sorter is not None


@patch("app.services.course_generator.YouTubeService")
def test_generate_course_with_mock(mock_youtube_service, test_db):
    """Тест генерации курса с моком YouTube API"""
    # 1. Настраиваем моки
    mock_youtube = Mock()
    mock_videos = [
        {
            "id": "video_1",
            "title": "Python основы",
            "description": "Описание видео 1",
            "channel": "Учебный канал",
            "url": "https://youtube.com/watch?v=1",
            "thumbnail": "thumb.jpg",
            "duration": 600,
            "view_count": 5000,
            "like_count": 100,
        },
        {
            "id": "video_2",
            "title": "Python функции",
            "description": "Описание видео 2",
            "channel": "Учебный канал",
            "url": "https://youtube.com/watch?v=2",
            "thumbnail": "thumb.jpg",
            "duration": 800,
            "view_count": 7000,
            "like_count": 150,
        },
    ]
    mock_youtube.search_videos.return_value = mock_videos
    mock_youtube_service.return_value = mock_youtube

    # 2. Создаём тестового пользователя

    user = UserFactory()
    test_db.commit()

    # 3. Генерируем курс
    generator = CourseGenerator(test_db)
    generator.youtube = mock_youtube  # подменяем реальный сервис

    course = generator.generate_course(
        topic="Python программирование", difficulty="beginner", user_id=user.id
    )

    # 4. Проверяем результат
    assert isinstance(course, Course)
    assert "Python" in course.title
    assert course.topic == "Python программирование"
    assert course.difficulty == "beginner"
    assert course.created_by == user.id
    assert len(course.modules) > 0

    # Проверяем, что созданы модули и уроки
    total_lessons = sum(len(module.lessons) for module in course.modules)
    assert total_lessons > 0

    # Проверяем, что видео данные сохранены
    first_lesson = course.modules[0].lessons[0]
    assert first_lesson.content_type == "video"
    assert "youtube.com" in first_lesson.content_url
    assert first_lesson.content_data is not None


def test_build_search_query(test_db):
    """Тест формирования поискового запроса"""
    generator = CourseGenerator(test_db)

    # Проверяем разные уровни сложности
    queries = {
        "beginner": generator._build_search_query("Python", "beginner"),
        "intermediate": generator._build_search_query("Python", "intermediate"),
        "advanced": generator._build_search_query("Python", "advanced"),
    }

    for difficulty, query in queries.items():
        assert "Python" in query
        assert "обучение" in query or "урок" in query
        assert query  # не пустой


@patch("app.services.course_generator.YouTubeService")
def test_generate_course_no_videos(mock_youtube_service, test_db):
    """Тест: если нет видео - должна быть ошибка"""
    mock_youtube = Mock()
    mock_youtube.search_videos.return_value = []
    mock_youtube_service.return_value = mock_youtube

    generator = CourseGenerator(test_db)
    generator.youtube = mock_youtube

    with pytest.raises(ValueError) as exc_info:
        generator.generate_course("Несуществующая тема", "beginner")

    assert "Не найдено видео" in str(exc_info.value)


@patch("app.services.youtube_service.settings")
def test_youtube_service_init(mock_settings):
    """Тест инициализации YouTube сервиса"""
    mock_settings.YOUTUBE_API_KEY = "test_key"
    service = YouTubeService()
    assert service.api_key == "test_key"
    assert service.youtube is not None


@patch("app.services.youtube_service.build")
def test_search_videos_with_api(mock_build):
    """Тест поиска видео через API (с моком)"""
    from app.services.youtube_service import YouTubeService

    # Настраиваем мок Google API
    mock_youtube = Mock()
    mock_search = Mock()
    mock_videos = Mock()

    mock_youtube.search.return_value = mock_search
    mock_search.list.return_value = mock_videos

    # Имитируем ответ API
    mock_videos.execute.return_value = {
        "items": [
            {
                "id": {"videoId": "test123"},
                "snippet": {
                    "title": "Test Video",
                    "description": "Test description",
                    "channelTitle": "Test Channel",
                    "thumbnails": {"high": {"url": "thumb.jpg"}},
                    "publishedAt": "2023-01-01T00:00:00Z",
                },
            }
        ]
    }

    mock_build.return_value = mock_youtube

    service = YouTubeService()
    service.api_key = "test_key"
    service.youtube = mock_youtube

    videos = service.search_videos("Python", max_results=5)

    assert len(videos) == 1
    assert videos[0]["title"] == "Test Video"
    assert "test123" in videos[0]["id"]


def test_search_videos_mock_mode():
    """Тест поиска видео в мок-режиме (без API ключа)"""
    service = YouTubeService()
    service.api_key = None  # имитируем отсутствие ключа

    videos = service.search_videos("Python", max_results=3)

    assert len(videos) == 3
    assert all("mock_" in video["id"] for video in videos)
    assert all("Python" in video["title"] for video in videos)


def test_parse_duration():
    """Тест парсинга длительности видео"""
    service = YouTubeService()

    test_cases = [
        ("PT5M30S", 330),  # 5 минут 30 секунд
        ("PT1H2M10S", 3730),  # 1 час 2 минуты 10 секунд
        ("invalid", 600),  # невалидный формат -> 600 по умолчанию
    ]

    for duration_str, expected in test_cases:
        result = service._parse_duration(duration_str)
        assert result == expected
