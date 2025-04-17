from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def yes_no_keyboard(language: str = "en"):
    if language == "ru":
        yes_btn = KeyboardButton("Да")
        no_btn = KeyboardButton("Нет")
    else:
        yes_btn = KeyboardButton("Yes")
        no_btn = KeyboardButton("No")
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(yes_btn, no_btn)
    return kb
