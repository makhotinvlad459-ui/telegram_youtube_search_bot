from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.crud.course import get_user_courses
from app.crud.user import get_or_create_user, get_user_by_telegram_id
from app.db.database import get_db


class CourseCreation(StatesGroup):
    waiting_for_topic = State()
    waiting_for_difficulty = State()


router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    db = next(get_db())
    user = get_or_create_user(
        db,
        {
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
        },
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 Создать курс", callback_data="create_course"
                )
            ],
            [InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        ]
    )

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 Я - бот для создания персонализированных курсов обучения.\n\n"
        "✨ Что я умею:\n"
        "• Создавать курсы по любой теме\n"
        "• Подбирать видеоуроки с YouTube\n"
        "• Структурировать материал от простого к сложному\n"
        "• Отслеживать твой прогресс\n\n"
        "🎯 Начни с создания первого курса!",
        reply_markup=keyboard,
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    help_text = """
📖 Доступные команды:

/start - Начать работу с ботом
/help - Показать это сообщение
/courses - Мои курсы
/newcourse - Создать новый курс
/profile - Мой профиль
/stats - Статистика обучения

💡 Просто напиши тему, по которой хочешь обучиться, и я создам для тебя курс!
    """
    await message.answer(help_text)


@router.callback_query(lambda c: c.data == "create_course")
async def callback_new_course(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки создания курса"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await callback.message.answer(
        "🎯 <b>Отлично! Давайте создадим курс!</b>\n\n"
        "📝 <b>Напишите тему, по которой хотите обучаться:</b>\n\n"
        "Примеры:\n"
        "• Python программирование\n"
        "• Веб-разработка\n"
        "• Машинное обучение\n"
        "• Английский язык\n"
        "• Финансовая грамотность",
        parse_mode="HTML",
    )
    await state.set_state(CourseCreation.waiting_for_topic)
    await callback.answer()


@router.callback_query(lambda c: c.data == "my_courses")
async def callback_my_courses(callback: types.CallbackQuery):
    """Обработка кнопки мои курсы"""
    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)

        if not user:
            await callback.message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        courses = get_user_courses(db, user.id)

        if not courses:
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="🎯 Создать первый курс", callback_data="create_course"
                        )
                    ]
                ]
            )

            await callback.message.answer(
                "📚 <b>У вас пока нет курсов</b>\n\n"
                "Создайте свой первый курс обучения!\n"
                "Это займет всего 2 минуты.",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return

        text = "📚 <b>Ваши курсы:</b>\n\n"

        for i, (course, user_course) in enumerate(courses[:10], 1):
            progress = user_course.completion_percentage
            status_icon = "✅" if user_course.completed else "📊"
            status_text = "Завершен" if user_course.completed else f"{progress:.1f}%"

            text += f"{i}. <b>{course.title}</b>\n"
            text += f"   🎯 {course.topic} | 📊 {course.difficulty}\n"
            text += f"   {status_icon} {status_text} | ⏱️ {course.estimated_hours} ч\n\n"

        if len(courses) > 10:
            text += f"📖 <i>И еще {len(courses) - 10} курсов...</i>\n\n"

        keyboard_buttons = []
        for i, (course, _) in enumerate(courses[:3], 1):
            keyboard_buttons.append(
                [
                    types.InlineKeyboardButton(
                        text=f"📖 {course.title[:15]}...",
                        callback_data=f"view_course_{course.id}",
                    )
                ]
            )

        keyboard_buttons.append(
            [
                types.InlineKeyboardButton(
                    text="🎯 Новый курс", callback_data="create_course"
                ),
                types.InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            ]
        )
        keyboard_buttons.append(
            [
                types.InlineKeyboardButton(
                    text="⬅️ В главное меню", callback_data="back_to_main"
                )  # Добавил
            ]
        )

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()

    await callback.answer()


@router.callback_query(lambda c: c.data == "back")
async def back_handler(callback: types.CallbackQuery):
    """Простой обработчик Назад"""
    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    # Показываем главное меню
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 Создать курс", callback_data="create_course"
                )
            ],
            [InlineKeyboardButton(text="📚 Мои курсы", callback_data="my_courses")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        ]
    )

    await callback.message.edit_text(
        f"👋 С возвращением, {callback.from_user.first_name}!\n\n"
        "🤖 Что будем делать?",
        reply_markup=keyboard,
    )
    await callback.answer()
