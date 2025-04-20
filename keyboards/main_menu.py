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


def main_menu_kb(locale: str = "ru") -> ReplyKeyboardMarkup:
    if locale == "ru":
        buttons = [
            [KeyboardButton("📚 Предметы"), KeyboardButton("📅 Расписание")],
            [KeyboardButton("⚙️ Настройки"), KeyboardButton("💳 Оплата")]
        ]
    else:
        buttons = [
            [KeyboardButton("📚 Subjects"), KeyboardButton("📅 Schedule")],
            [KeyboardButton("⚙️ Settings"), KeyboardButton("💳 Payment")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)