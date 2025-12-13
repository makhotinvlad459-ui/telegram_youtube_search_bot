import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import AsyncMock, Mock, patch

import pytest


# Тест 1: Простейший тест с моком
@pytest.mark.asyncio
async def test_start_command_simple():
    """Самый простой тест команды /start"""
    # Создаём моки
    message = AsyncMock()
    message.from_user = Mock(
        id=123456, username="testuser", first_name="Test", last_name="User"
    )
    message.answer = AsyncMock()

    # Мокаем get_db
    mock_db = Mock()

    # Мокаем get_or_create_user
    mock_user = Mock()
    mock_user.id = 1
    mock_user.telegram_id = 123456

    # Используем patch для подмены импортов
    with patch("app.bot.handlers.start.get_db", return_value=iter([mock_db])):
        with patch("app.bot.handlers.start.get_or_create_user", return_value=mock_user):
            # Импортируем хэндлер прямо здесь
            from app.bot.handlers.start import cmd_start

            await cmd_start(message)

    # Проверяем, что бот ответил
    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    assert "Привет" in call_text or "👋" in call_text


# Тест 2: Тест помощи
@pytest.mark.asyncio
async def test_help_command():
    """Тест команды /help"""
    message = AsyncMock()
    message.answer = AsyncMock()

    from app.bot.handlers.start import cmd_help

    await cmd_help(message)

    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    assert "команды" in call_text.lower() or "help" in call_text.lower()


# Тест 3: Тест кнопки "Мои курсы"
@pytest.mark.asyncio
async def test_my_courses_button():
    """Тест обработки кнопки 'Мои курсы'"""
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.from_user = Mock(id=123456)
    callback.answer = AsyncMock()

    # Мокаем всё, что нужно
    mock_db = Mock()
    mock_user = Mock()
    mock_user.id = 1

    with patch("app.bot.handlers.start.get_db", return_value=iter([mock_db])):
        with patch(
            "app.bot.handlers.start.get_user_by_telegram_id", return_value=mock_user
        ):
            with patch("app.bot.handlers.start.get_user_courses", return_value=[]):
                from app.bot.handlers.start import callback_my_courses

                await callback_my_courses(callback)

    # Проверяем ответ
    assert callback.message.answer.called
    call_text = callback.message.answer.call_args[0][0]
    assert "курс" in call_text.lower()


# tests/test_handlers.py - исправленный тест
@pytest.mark.asyncio
async def test_profile_command():
    """Тест команды /profile"""
    message = AsyncMock()
    message.from_user = Mock(id=123456, username="test", first_name="Test")
    message.answer = AsyncMock()

    mock_db = Mock()

    # Мок для пользователя
    mock_user = Mock()
    mock_user.id = 1
    mock_user.telegram_id = 123456
    mock_user.username = "test"
    mock_user.first_name = "Test"

    # Мок для get_user_stats
    mock_stats = {
        "experience_points": 100,
        "level": 2,
        "total_courses": 3,
        "completed_courses": 1,
        "completed_lessons": 10,
        "total_time_watched_minutes": 120,
        "recent_courses_7_days": 1,
        "completion_rate": 33.3,
        "user_id": 1,
        "username": "test",
        "first_name": "Test",
    }

    # Патчим всё что нужно
    with patch("app.bot.handlers.profile.get_db", return_value=iter([mock_db])):
        with patch(
            "app.bot.handlers.profile.get_or_create_user", return_value=mock_user
        ):
            with patch(
                "app.bot.handlers.profile.get_user_stats", return_value=mock_stats
            ):
                from app.bot.handlers.profile import cmd_profile

                await cmd_profile(message)

    # Проверяем ответ
    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    # Должно содержать данные профиля
    assert (
        "Профиль" in call_text
        or "статистика" in call_text.lower()
        or "уровень" in call_text.lower()
    )


# Тест 5: Тест статистики
@pytest.mark.asyncio
async def test_stats_command():
    """Тест команды /stats"""
    message = AsyncMock()
    message.from_user = Mock(id=123456, username="test", first_name="Test")
    message.answer = AsyncMock()

    mock_db = Mock()
    mock_user = Mock()
    mock_user.id = 1

    mock_stats = {
        "experience_points": 150,
        "level": 2,
        "total_courses": 3,
        "completed_courses": 1,
    }

    with patch("app.bot.handlers.profile.get_db", return_value=iter([mock_db])):
        with patch(
            "app.bot.handlers.profile.get_or_create_user", return_value=mock_user
        ):
            with patch(
                "app.bot.handlers.profile.get_user_stats", return_value=mock_stats
            ):
                from app.bot.handlers.profile import show_statistics

                await show_statistics(message)

    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    assert "статистика" in call_text.lower() or "опыт" in call_text.lower()


# Тест 6: Тест обработки обычных сообщений
@pytest.mark.asyncio
async def test_other_messages():
    """Тест обработки случайных сообщений"""
    message = AsyncMock()
    message.text = "Что ты умеешь?"
    message.from_user = Mock(first_name="Test")
    message.answer = AsyncMock()

    from app.bot.handlers.common import handle_other_messages

    await handle_other_messages(message)

    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    assert "написали" in call_text.lower() or "Привет" in call_text
