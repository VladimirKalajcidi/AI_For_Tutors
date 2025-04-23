from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(language: str = "ru"):
    if language == "ru":
        buttons = [
            [KeyboardButton(text="👨‍🎓 Ученики")],
            [KeyboardButton(text="📆 Расписание недели")],
            [KeyboardButton(text="💳 Оплата")],
            [KeyboardButton(text="⚙️ Настройки")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="👨‍🎓 Students")],
            [KeyboardButton(text="📆 Weekly Schedule")],
            [KeyboardButton(text="💳 Payment")],
            [KeyboardButton(text="⚙️ Settings")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_menu_kb(locale: str = "ru") -> ReplyKeyboardMarkup:
    if locale == "ru":
        buttons = [
            [KeyboardButton("👨‍🎓 Ученики"), KeyboardButton("📆 Расписание недели")],
            [KeyboardButton("➕ Добавить урок")],
            [KeyboardButton("⚙️ Настройки"), KeyboardButton("💳 Оплата")]
        ]
    else:
        buttons = [
            [KeyboardButton("👨‍🎓 Students"), KeyboardButton("📆 Weekly Schedule")],
            [KeyboardButton("➕ Add Lesson")],
            [KeyboardButton("⚙️ Settings"), KeyboardButton("💳 Payment")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
