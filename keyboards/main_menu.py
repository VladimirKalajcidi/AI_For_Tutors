from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(language: str = "ru"):
    buttons = [
        [KeyboardButton(text="👨‍🎓 Ученики")],
        [KeyboardButton(text="📆 Расписание недели")],
        [KeyboardButton(text="💳 Оплата")],
        [KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_menu_kb(locale: str = "ru") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("👨‍🎓 Ученики"), KeyboardButton("📆 Расписание недели")],
        [KeyboardButton("➕ Добавить занятие")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("💳 Оплата")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
