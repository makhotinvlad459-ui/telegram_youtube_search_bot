from aiogram import F, Router, types

from app.crud.course import (
    enroll_user_to_course,
    get_course_by_id,
    get_user_progress_for_course,
    update_course_progress,
)
from app.crud.user import get_user_by_telegram_id, mark_lesson_completed
from app.db.database import get_db
from app.db.models import Lesson, Module

router = Router()


@router.callback_query(F.data.startswith("start_learning_"))
async def start_learning(callback: types.CallbackQuery):
    """Начать обучение по курсу"""
    course_id = int(callback.data.replace("start_learning_", ""))

    db = next(get_db())
    try:
        course = get_course_by_id(db, course_id)
        user = get_user_by_telegram_id(db, callback.from_user.id)

        if not course or not user:
            await callback.answer("❌ Курс или пользователь не найден", show_alert=True)
            return

        # Записываем пользователя на курс если еще не записан
        enroll_user_to_course(db, user.id, course_id)

        # Получаем первый урок
        if course.modules and course.modules[0].lessons:
            first_module = course.modules[0]
            first_lesson = first_module.lessons[0]

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="▶️ Смотреть урок", url=first_lesson.content_url
                        ),
                        types.InlineKeyboardButton(
                            text="✅ Завершить урок",
                            callback_data=f"complete_lesson_{first_lesson.id}",
                        ),
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="📋 Содержание",
                            callback_data=f"view_course_{course_id}",
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="⬅️ Назад", callback_data=f"view_course_{course_id}"
                        )
                    ],
                ]
            )

            await callback.message.edit_text(
                f"🎬 <b>НАЧАЛО ОБУЧЕНИЯ</b>\n\n"
                f"📚 <b>Курс:</b> {course.title}\n"
                f"📦 <b>Модуль 1:</b> {first_module.title}\n\n"
                f"📹 <b>Урок 1:</b> {first_lesson.title}\n"
                f"⏱️ <b>Длительность:</b> {first_lesson.duration_minutes} минут\n\n"
                f"Нажмите '▶️ Смотреть урок' для перехода к видео",
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text("❌ В курсе нет доступных уроков")
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson_handler(callback: types.CallbackQuery):
    """Отметить урок как завершенный и показать следующий"""
    lesson_id = int(callback.data.replace("complete_lesson_", ""))

    db = next(get_db())
    try:
        # Получаем пользователя и урок
        user = get_user_by_telegram_id(db, callback.from_user.id)
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

        if not user or not lesson:
            await callback.answer("❌ Урок или пользователь не найден", show_alert=True)
            return

        mark_lesson_completed(
            db, user.id, lesson_id, watched_seconds=lesson.duration_minutes * 60
        )

        # Обновляем прогресс курса
        course_id = lesson.module.course_id
        user_course = update_course_progress(db, user.id, course_id)

        # Получаем курс для информации
        course = get_course_by_id(db, course_id)

        # Ищем следующий урок в текущем модуле
        next_lesson = (
            db.query(Lesson)
            .filter(
                Lesson.module_id == lesson.module_id,
                Lesson.order_index > lesson.order_index,
            )
            .order_by(Lesson.order_index)
            .first()
        )

        if next_lesson:
            # Есть следующий урок в том же модуле
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="▶️ Следующий урок", url=next_lesson.content_url
                        ),
                        types.InlineKeyboardButton(
                            text="✅ Завершить",
                            callback_data=f"complete_lesson_{next_lesson.id}",
                        ),
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="📋 Содержание курса",
                            callback_data=f"view_course_{course_id}",
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="⬅️ Назад к курсу",
                            callback_data=f"view_course_{course_id}",
                        )
                    ],
                ]
            )

            progress_percent = user_course.completion_percentage if user_course else 0

            await callback.message.edit_text(
                f"✅ <b>УРОК ЗАВЕРШЕН!</b>\n\n"
                f"📚 <b>Курс:</b> {course.title if course else 'Неизвестно'}\n"
                f"📦 <b>Модуль:</b> {lesson.module.title}\n"
                f"📝 <b>Завершен:</b> {lesson.title}\n\n"
                f"📊 <b>Прогресс курса:</b> {progress_percent:.1f}%\n\n"
                f"➡️ <b>Следующий урок:</b>\n"
                f"{next_lesson.title}\n"
                f"⏱️ {next_lesson.duration_minutes} минут",
                reply_markup=keyboard,
                parse_mode="HTML",
            )

        else:
            # Нужно искать следующий модуль
            next_module = (
                db.query(Module)
                .filter(
                    Module.course_id == course_id,
                    Module.order_index > lesson.module.order_index,
                )
                .order_by(Module.order_index)
                .first()
            )

            if next_module and next_module.lessons:
                # Есть следующий модуль с уроками
                next_lesson_in_module = next_module.lessons[0]

                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="▶️ Следующий урок",
                                url=next_lesson_in_module.content_url,
                            ),
                            types.InlineKeyboardButton(
                                text="✅ Завершить",
                                callback_data=f"complete_lesson_{next_lesson_in_module.id}",
                            ),
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="📋 Содержание курса",
                                callback_data=f"view_course_{course_id}",
                            )
                        ],
                    ]
                )

                progress_percent = (
                    user_course.completion_percentage if user_course else 0
                )

                await callback.message.edit_text(
                    f"🎉 <b>МОДУЛЬ ЗАВЕРШЕН!</b>\n\n"
                    f"📚 <b>Курс:</b> {course.title if course else 'Неизвестно'}\n"
                    f"✅ <b>Завершен модуль:</b> {lesson.module.title}\n\n"
                    f"📊 <b>Прогресс курса:</b> {progress_percent:.1f}%\n\n"
                    f"➡️ <b>Новый модуль:</b> {next_module.title}\n"
                    f"📝 <b>Первый урок:</b> {next_lesson_in_module.title}\n"
                    f"⏱️ {next_lesson_in_module.duration_minutes} минут",
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )

            else:
                # Курс завершен!
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="🏆 Курс завершен!",
                                callback_data=f"course_completed_{course_id}",
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="🎯 Новый курс", callback_data="create_course"
                            )
                        ],
                    ]
                )

                await callback.message.edit_text(
                    f"🎉 <b>КУРС ПОЛНОСТЬЮ ЗАВЕРШЕН!</b>\n\n"
                    f"🏆 <b>Поздравляю!</b>\n"
                    f"Вы завершили курс: {course.title if course else 'Неизвестно'}\n\n"
                    f"⭐ <b>Получен опыт!</b>\n"
                    f"📈 <b>Уровень повышен!</b>\n\n"
                    f"Создайте новый курс чтобы продолжить обучение!",
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )

        await callback.answer("✅ Урок отмечен как завершенный!")

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("course_completed_"))
async def course_completed_handler(callback: types.CallbackQuery):
    """Обработка завершения курса"""
    course_id = int(callback.data.replace("course_completed_", ""))

    db = next(get_db())
    try:
        course = get_course_by_id(db, course_id)

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🎯 Создать новый курс", callback_data="create_course"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📚 Мои курсы", callback_data="list_courses"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📊 Статистика", callback_data="show_stats"
                    )
                ],
            ]
        )

        await callback.message.edit_text(
            f"🏆 <b>ОТЛИЧНАЯ РАБОТА!</b>\n\n"
            f"Вы успешно завершили курс:\n"
            f"<b>{course.title if course else 'Курс'}</b>\n\n"
            f"🎯 <b>Что дальше?</b>\n"
            f"• Создайте новый курс\n"
            f"• Посмотрите свою статистику\n"
            f"• Изучите другие курсы",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as e:
        await callback.answer("❌ Ошибка при обработке")
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data.startswith("course_progress_"))
async def show_course_progress(callback: types.CallbackQuery):
    """Показать детальный прогресс по курсу"""
    course_id = int(callback.data.replace("course_progress_", ""))

    db = next(get_db())
    try:
        user = get_user_by_telegram_id(db, callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        progress = get_user_progress_for_course(db, user.id, course_id)
        course = get_course_by_id(db, course_id)

        if not progress or not course:
            await callback.answer("❌ Прогресс не найден", show_alert=True)
            return

        # Прогресс бар
        percent = progress["completion_percentage"]
        bar_length = 15
        filled = int(percent / 100 * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        text = f"📊 <b>ПРОГРЕСС КУРСА</b>\n\n"
        text += f"📚 <b>{course.title}</b>\n"
        text += f"✅ <b>Завершено:</b> {progress['completed_lessons']}/{progress['total_lessons']} уроков\n"
        text += f"📈 <b>Прогресс:</b> {percent:.1f}%\n"
        text += f"   [{bar}]\n"
        text += (
            f"⏱️ <b>Просмотрено:</b> {progress['total_watch_time_minutes']} минут\n\n"
        )

        text += "📦 <b>Прогресс по модулям:</b>\n"
        for module in progress["modules"]:
            completed = sum(1 for lesson in module["lessons"] if lesson["completed"])
            total = len(module["lessons"])
            module_percent = (completed / total * 100) if total > 0 else 0

            # Мини-прогресс бар для модуля
            module_bar_length = 8
            module_filled = int(module_percent / 100 * module_bar_length)
            module_bar = "█" * module_filled + "░" * (module_bar_length - module_filled)

            text += f"\n{module['title']}\n"
            text += f"  [{module_bar}] {completed}/{total} ({module_percent:.0f}%)\n"

            # Показать завершенные уроки
            for lesson in module["lessons"]:
                if lesson["completed"]:
                    text += f"    ✅ {lesson['title'][:30]}...\n"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🎬 Продолжить обучение",
                        callback_data=f"start_learning_{course_id}",
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📚 К курсу", callback_data=f"view_course_{course_id}"
                    ),
                    types.InlineKeyboardButton(
                        text="⬅️ Назад", callback_data="list_courses"
                    ),
                ],
            ]
        )

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
    finally:
        db.close()

    await callback.answer()
