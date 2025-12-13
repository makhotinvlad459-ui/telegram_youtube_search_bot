from aiogram import Dispatcher

from .common import router as common_router
from .courses import router as courses_router
from .learning import router as learning_router
from .profile import router as profile_router
from .start import router as start_router


def register_handlers(dp: Dispatcher):
    """Регистрация всех роутеров"""
    dp.include_router(start_router)
    dp.include_router(courses_router)
    dp.include_router(profile_router)
    dp.include_router(learning_router)
    dp.include_router(common_router)
