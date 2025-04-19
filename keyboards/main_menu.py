from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(language: str = "ru"):
    if language == "ru":
        buttons = [
            [KeyboardButton(text="👨‍🎓 Ученики")],
            [KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="💳 Оплата")],
            [KeyboardButton(text="⚙️ Настройки")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="👨‍🎓 Students")],
            [KeyboardButton(text="📅 Schedule")],
            [KeyboardButton(text="💳 Bill")],
            [KeyboardButton(text="⚙️ Settings")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
