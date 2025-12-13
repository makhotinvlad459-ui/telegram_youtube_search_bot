import logging

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.crud.course import (
    enroll_user_to_course,
    get_course_by_id,
    get_user_courses,
)
from app.crud.user import get_or_create_user, get_user_by_telegram_id
from app.db.database import get_db
from app.worker.celery_app import celery_app
from app.worker.tasks import generate_course_task

logger = logging.getLogger(__name__)
router = Router()


# Состояния
class CourseCreation(StatesGroup):
    waiting_for_topic = State()
    waiting_for_difficulty = State()


# ==================== СОЗДАНИЕ КУРСА ====================


@router.callback_query(F.data == "create_course")
@router.message(Command("newcourse"))
async def start_course_creation(
    callback_or_message: types.CallbackQuery | types.Message, state: FSMContext
):
    """Начать создание курса"""
    if isinstance(callback_or_message, types.CallbackQuery):
        message = callback_or_message.message
        await callback_or_message.answer()
    else:
        message = callback_or_message

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )

    await message.answer(
        "🎯 <b>Отлично! Давайте создадим курс!</b>\n\n"
        "📝 <b>Напишите тему, по которой хотите обучаться:</b>\n\n"
        "Примеры:\n"
        "• Python программирование\n"
        "• Веб-разработка\n"
        "• Машинное обучение\n"
        "• Английский язык\n"
        "• Финансовая грамотность",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(CourseCreation.waiting_for_topic)


@router.message(CourseCreation.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    """Обработать ввод темы"""
    topic = message.text.strip()

    if len(topic) < 3:
        await message.answer(
            "❌ Тема слишком короткая. Минимум 3 символа. Попробуйте еще раз:"
        )
        return

    await state.update_data(topic=topic)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="👶 Начинающий", callback_data="difficulty_beginner"
                ),
                types.InlineKeyboardButton(
                    text="📈 Средний", callback_data="difficulty_intermediate"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🚀 Продвинутый", callback_data="difficulty_advanced"
                ),
                types.InlineKeyboardButton(
                    text="🎯 Любой уровень", callback_data="difficulty_any"
                ),
            ],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="create_course")],
        ]
    )

    await message.answer(
        f"✅ <b>Тема:</b> {topic}\n\n"
        "📊 <b>Выберите уровень сложности:</b>\n\n"
        "👶 <b>Начинающий</b> - основы, введение\n"
        "📈 <b>Средний</b> - практика, углубление\n"
        "🚀 <b>Продвинутый</b> - экспертные знания\n"
        "🎯 <b>Любой уровень</b> - смешанные материалы",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(CourseCreation.waiting_for_difficulty)


@router.callback_query(F.data.startswith("difficulty_"))
async def process_difficulty(callback: types.CallbackQuery, state: FSMContext):
    """Обработать выбор сложности"""
    difficulty = callback.data.replace("difficulty_", "")

    if difficulty == "any":
        difficulty = "beginner"

    difficulty_names = {
        "beginner": "👶 Начинающий",
        "intermediate": "📈 Средний",
        "advanced": "🚀 Продвинутый",
    }

    data = await state.get_data()
    topic = data.get("topic", "")

    # Редактируем сообщение с прогрессом
    try:
        await callback.message.edit_text(
            f"⏳ <b>Создаю курс...</b>\n\n"
            f"📚 <b>Тема:</b> {topic}\n"
            f"📊 <b>Уровень:</b> {difficulty_names.get(difficulty, difficulty)}\n\n"
            "🤖 <b>Что я делаю:</b>\n"
            "1. 🔍 Ищу лучшие видео на YouTube\n"
            "2. 📊 Анализирую и сортирую материал\n"
            "3. 🏗️ Создаю структуру курса\n"
            "4. 🎯 Оптимизирую для обучения\n\n"
            "<i>Это займет 1-2 минуты...</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass  # Игнорируем ошибку если сообщение уже изменено

    # Получаем пользователя
    db = next(get_db())
    try:
        user = get_or_create_user(
            db,
            {
                "telegram_id": callback.from_user.id,
                "username": callback.from_user.username,
                "first_name": callback.from_user.first_name,
                "last_name": callback.from_user.last_name,
            },
        )

        # Отправляем задачу в Celery
        result = generate_course_task.delay(
            topic=topic, difficulty=difficulty, user_id=user.id
        )

        task_id = result.id
        await state.update_data(task_id=task_id)

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔄 Проверить статус",
                        callback_data=f"check_status_{task_id}",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📚 Мои курсы", callback_data="my_courses"
                    )
                ],
            ]
        )

        await callback.message.answer(
            f"✅ <b>Задача отправлена!</b>\n\n"
            f"📋 <b>ID задачи:</b> <code>{task_id[:12]}...</code>\n\n"
            "Я пришлю уведомление когда курс будет готов.\n"
            "Можете проверить статус в любое время.",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка отправки задачи в Celery: {e}")
        await callback.message.answer(
            f"❌ <b>Ошибка при создании курса:</b>\n"
            f"{str(e)[:200]}\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML",
        )
    finally:
        db.close()

    await state.clear()
    await callback.answer()


# ==================== ПРОВЕРКА СТАТУСА ====================


@router.callback_query(F.data.startswith("check_status_"))
async def check_course_status(callback: types.CallbackQuery):
    """Проверить статус создания курса"""
    task_id = callback.data.replace("check_status_", "")

    try:
        async_result = celery_app.AsyncResult(task_id)

        if async_result.ready():
            result = async_result.get()

            if result.get("status") == "success":
                course_id = result.get("course_id")
                course_title = result.get("title", "Новый курс")

                # Получаем курс из БД
                db = next(get_db())
                try:
                    course = get_course_by_id(db, course_id)

                    if course:
                        # Записываем пользователя на курс
                        user = get_user_by_telegram_id(db, callback.from_user.id)
                        if user:
                            enroll_user_to_course(db, user.id, course_id)

                    keyboard = types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="📚 Посмотреть курс",
                                    callback_data=f"view_course_{course_id}",
                                )
                            ],
                            [
                                types.InlineKeyboardButton(
                                    text="🎬 Начать обучение",
                                    callback_data=f"start_learning_{course_id}",
                                )
                            ],
                            [
                                types.InlineKeyboardButton(
                                    text="🎯 Новый курс", callback_data="create_course"
                                )
                            ],
                        ]
                    )

                    await callback.message.answer(
                        f"🎉 <b>КУРС ГОТОВ!</b>\n\n"
                        f"📚 <b>{course_title}</b>\n"
                        f"📦 <b>Модулей:</b> {result.get('modules', 0)}\n"
                        f"📝 <b>Уроков:</b> {result.get('lessons', 0)}\n"
                        f"🎯 <b>Тема:</b> {result.get('topic', '')}\n"
                        f"📊 <b>Уровень:</b> {result.get('difficulty', '')}\n\n"
                        f"✅ <b>Курс добавлен в вашу библиотеку!</b>",
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                finally:
                    db.close()
            else:
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="🔄 Попробовать снова",
                                callback_data="create_course",
                            )
                        ]
                    ]
                )

                await callback.message.answer(
                    f"❌ <b>Ошибка при создании курса</b>\n\n"
                    f"<b>Причина:</b> {result.get('error', 'Неизвестная ошибка')}\n\n"
                    f"Попробуйте создать курс еще раз или выберите другую тему.",
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
        else:
            status = async_result.state
            progress = ""

            if status == "PROGRESS":
                info = async_result.info
                if info and "message" in info:
                    progress = f"\n\n📊 <b>{info['message']}</b>"

            status_text = {
                "PENDING": "⏳ Ожидает выполнения",
                "STARTED": "🚀 Началось выполнение",
                "PROGRESS": "🔄 Выполняется",
            }.get(status, status)

            await callback.answer(
                f"{status_text}{progress}\n\n" f"ID задачи: {task_id[:8]}...",
                show_alert=True,
            )

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)


# ==================== РАБОТА С КУРСАМИ ====================


@router.callback_query(F.data == "my_courses")
@router.callback_query(F.data == "list_courses")
@router.message(Command("mycourses", "courses"))
async def list_user_courses(callback_or_message: types.CallbackQuery | types.Message):
    """Показать курсы пользователя"""
    if isinstance(callback_or_message, types.CallbackQuery):
        message = callback_or_message.message
        await callback_or_message.answer()
    else:
        message = callback_or_message

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
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

            await message.answer(
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
                )
            ]
        )

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()


@router.callback_query(F.data.startswith("view_course_"))
async def view_course_details(callback: types.CallbackQuery):
    """Просмотр деталей курса"""
    course_id = int(callback.data.replace("view_course_", ""))

    db = next(get_db())
    try:
        course = get_course_by_id(db, course_id)

        if not course:
            await callback.answer("❌ Курс не найден", show_alert=True)
            return

        text = f"📚 <b>{course.title}</b>\n\n"

        if course.description:
            text += f"📝 {course.description}\n\n"

        text += f"🎯 <b>Тема:</b> {course.topic}\n"
        text += f"📊 <b>Уровень:</b> {course.difficulty}\n"
        text += f"⏱️ <b>Часов:</b> {course.estimated_hours}\n"
        text += f"📅 <b>Создан:</b> {course.created_at.strftime('%d.%m.%Y')}\n\n"

        text += "📦 <b>Структура курса:</b>\n"
        for i, module in enumerate(course.modules, 1):
            text += f"\n{i}. <b>{module.title}</b>\n"
            for j, lesson in enumerate(module.lessons, 1):
                text += f"   📹 {j}. {lesson.title} ({lesson.duration_minutes} мин)\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🎬 Начать обучение",
                        callback_data=f"start_learning_{course.id}",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📊 Прогресс", callback_data=f"course_progress_{course.id}"
                    ),
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", callback_data="my_courses"
                    ),
                ],
            ]
        )
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "back_to_courses")
async def back_to_courses_handler(callback: types.CallbackQuery):
    """Вернуться к списку курсов"""
    await list_user_courses(callback)


def create_course_with_task(db, topic: str, difficulty: str, user_id: int) -> str:
    """Создать курс через Celery задачу"""
    result = generate_course_task.delay(
        topic=topic, difficulty=difficulty, user_id=user_id
    )
    return result.id
