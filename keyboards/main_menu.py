from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👨‍🎓 Ученики")],
        [KeyboardButton(text="📆 Расписание недели")],
        [KeyboardButton(text="💳 Оплата")],
        [KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_menu_kb(locale: str = "ru") -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👨‍🎓 Ученики"), KeyboardButton(text="📆 Расписание недели")],
        [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="💳 Оплата")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
