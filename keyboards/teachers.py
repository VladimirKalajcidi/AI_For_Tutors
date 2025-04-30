from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def teacher_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")]
    ])

def edit_teacher_field_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data="edit_teacher_field:name")],
        [InlineKeyboardButton(text="Фамилия", callback_data="edit_teacher_field:surname")],
        [InlineKeyboardButton(text="Отчество", callback_data="edit_teacher_field:patronymic")],
        [InlineKeyboardButton(text="Дата рождения", callback_data="edit_teacher_field:birth_date")],
        [InlineKeyboardButton(text="Телефон", callback_data="edit_teacher_field:phone")],
        [InlineKeyboardButton(text="Email", callback_data="edit_teacher_field:email")],
        [InlineKeyboardButton(text="Предметы", callback_data="edit_teacher_field:subjects")],
        [InlineKeyboardButton(text="Профессия", callback_data="edit_teacher_field:occupation")],
        [InlineKeyboardButton(text="Место работы", callback_data="edit_teacher_field:workplace")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
    ])

def settings_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🔗 Подключить Яндекс.Диск", callback_data="link_yandex_disk")],
        # [InlineKeyboardButton(text="🔗 Подключить Google Calendar", callback_data="google_auth")],
        # [InlineKeyboardButton(text="🌍 Change Language", callback_data="set_lang")],
        [InlineKeyboardButton(text="🗑 Удалить аккаунт", callback_data="delete_account")],
    ])
