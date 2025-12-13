from aiogram import Router, types

router = Router()


@router.message()
async def handle_other_messages(message: types.Message):
    """Обработка всех остальных сообщений"""
    if message.text:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🎯 Создать курс", callback_data="create_course"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="📚 Мои курсы", callback_data="list_courses"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="❓ Помощь", callback_data="show_help"
                    )
                ],
            ]
        )

        await message.answer(
            f"🤖 <b>Привет, {message.from_user.first_name}!</b>\n\n"
            f"Вы написали: <i>{message.text}</i>\n\n"
            "Используйте кнопки ниже или команды:\n"
            "/start - Главное меню\n"
            "/newcourse - Создать курс\n"
            "/mycourses - Мои курсы\n"
            "/help - Справка",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
