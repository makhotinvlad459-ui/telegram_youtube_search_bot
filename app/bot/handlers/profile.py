from aiogram import F, Router, types
from aiogram.filters import Command

from app.crud.user import get_or_create_user, get_user_stats
from app.db.database import get_db

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показать профиль пользователя"""
    db = next(get_db())
    try:

        user = get_or_create_user(
            db,
            {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            },
        )

        if not user:
            await message.answer("❌ Ошибка регистрации")
            return

        stats = get_user_stats(db, user.id)

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📊 Статистика", callback_data="stats"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📚 Мои курсы", callback_data="my_courses"
                    )
                ],
            ]
        )

        text = f"👤 <b>Профиль пользователя</b>\n\n"
        text += f"🆔 ID: {user.telegram_id}\n"
        text += f"👤 Имя: {user.first_name or 'Не указано'}\n"
        if user.username:
            text += f"📱 Username: @{user.username}\n"

        exp = stats.get("experience_points", 0)
        level = stats.get("level", 1)
        text += f"\n⭐ <b>Уровень:</b> {level}\n"
        text += f"🎯 <b>Опыт:</b> {exp}/100\n"

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()


@router.callback_query(F.data == "stats")
@router.message(Command("stats"))
async def show_statistics(callback_or_message: types.CallbackQuery | types.Message):
    """Показать статистику"""
    if isinstance(callback_or_message, types.CallbackQuery):
        message = callback_or_message.message
        await callback_or_message.answer()
    else:
        message = callback_or_message

    db = next(get_db())
    try:
        from app.crud.user import get_or_create_user

        user = get_or_create_user(
            db,
            {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            },
        )

        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        stats = get_user_stats(db, user.id)

        exp = stats.get("experience_points", 0)
        level = stats.get("level", 1)
        exp_to_next = 100 - (exp % 100)

        # Прогресс бар
        progress = exp % 100
        bar_length = 15
        filled = int(progress / 100 * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        text = f"📊 <b>ВАША СТАТИСТИКА</b>\n\n"
        text += f"👤 <b>Пользователь:</b> {user.first_name or 'Аноним'}\n"
        text += f"⭐ <b>Уровень:</b> {level}\n"
        text += f"🎯 <b>Опыт:</b> {exp} ({exp_to_next} до след. уровня)\n"
        text += f"   [{bar}] {progress}%\n\n"

        text += f"📚 <b>Курсов всего:</b> {stats.get('total_courses', 0)}\n"
        text += f"✅ <b>Завершено курсов:</b> {stats.get('completed_courses', 0)}\n"
        text += f"📝 <b>Завершено уроков:</b> {stats.get('completed_lessons', 0)}\n"
        text += (
            f"⏱️ <b>Просмотрено:</b> {stats.get('total_time_watched_minutes', 0)} мин\n"
        )
        text += (
            f"📈 <b>За 7 дней:</b> {stats.get('recent_courses_7_days', 0)} курсов\n\n"
        )

        completion_rate = stats.get("completion_rate", 0)
        if completion_rate > 0:
            text += f"🏆 <b>Процент завершения:</b> {completion_rate:.1f}%\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📚 Мои курсы", callback_data="my_courses"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="🎯 Новый курс", callback_data="create_course"
                    )
                ],
            ]
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()


@router.message(Command("myid"))
async def cmd_myid(message: types.Message):
    """Показать мой Telegram ID"""
    await message.answer(
        f"👤 <b>Твои данные:</b>\n\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"👤 Имя: {message.from_user.first_name}\n"
        f"📱 Username: @{message.from_user.username or 'нет'}\n",
        parse_mode="HTML",
    )
