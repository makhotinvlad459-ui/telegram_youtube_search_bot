import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import time
from unittest.mock import Mock, patch

import pytest

# ============ ИСПРАВЛЕННЫЕ ТЕСТЫ ============


def test_ping_task():
    """Простейший тест задачи ping"""
    from app.worker.tasks import ping_task

    result = ping_task()
    assert result["status"] == "pong"
    print("✅ test_ping_task - ПРОШЁЛ")
    return True


def test_test_task():
    """Тест задачи test_task"""
    from app.worker.tasks import test_task

    result = test_task("Hello World")
    assert result["status"] == "success"
    assert "Hello World" in result["message"]
    print("✅ test_test_task - ПРОШЁЛ")
    return True


def test_debug_task_fixed():
    """ИСПРАВЛЕННЫЙ тест задачи debug_task"""
    from app.worker.tasks import debug_task

    # Правильный мок для Celery задачи
    class MockTask:
        def __init__(self):
            self.request = Mock()
            self.request.id = "test_debug_123"

    mock_task = MockTask()
    result = debug_task(mock_task)

    assert result["status"] == "success"
    assert "Celery is working" in result["message"]
    print("✅ test_debug_task_fixed - ПРОШЁЛ")
    return True


def test_long_task_fixed():
    """ИСПРАВЛЕННЫЙ тест длительной задачи"""
    from app.worker.tasks import long_task

    class MockTask:
        def __init__(self):
            self.request = Mock()
            self.update_state = Mock()

    mock_task = MockTask()

    # Запускаем с очень маленькой задержкой
    result = long_task(mock_task, seconds=0.1)  # 0.1 секунды вместо 1

    assert result["status"] == "completed"
    assert result["seconds"] == 0.1
    assert mock_task.update_state.called
    print("✅ test_long_task_fixed - ПРОШЁЛ")
    return True


def test_celery_app_config():
    """Тест конфигурации Celery"""
    from app.worker.celery_app import celery_app

    assert celery_app.main == "learning_worker"
    assert "app.worker.tasks" in celery_app.conf.include
    print("✅ test_celery_app_config - ПРОШЁЛ")
    return True


# ============ ПРОСТЫЕ ТЕСТЫ ДЛЯ Pytest ============


# Эти тесты работают с pytest
def test_ping_pytest():
    from app.worker.tasks import ping_task

    result = ping_task()
    assert result["status"] == "pong"


def test_test_pytest():
    from app.worker.tasks import test_task

    result = test_task("pytest test")
    assert result["status"] == "success"


# ============ ЗАПУСК ВСЕХ ТЕСТОВ ============

if __name__ == "__main__":
    print("🚀 Запуск Celery тестов...\n")

    tests = [
        ("Ping task", test_ping_task),
        ("Test task", test_test_task),
        ("Debug task", test_debug_task_fixed),
        ("Long task", test_long_task_fixed),
        ("Celery config", test_celery_app_config),
    ]

    all_passed = True
    for name, test_func in tests:
        try:
            print(f"▶️  {name}...")
            if test_func():
                print(f"   ✅ Успех\n")
            else:
                print(f"   ❌ Провал\n")
                all_passed = False
        except Exception as e:
            print(f"   ❌ Ошибка: {e}\n")
            all_passed = False

    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print("⚠️  Некоторые тесты не прошли")

    print(f"\n📊 Запусти через pytest для детальной информации:")
    print("  pytest tests/test_celery_final.py -v")
