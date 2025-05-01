from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def subject_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["Математика", "Физика"],
        ["Русский язык", "Информатика"],
        ["Английский язык", "Химия"],
        ["Биология", "История"],
        ["Обществознание"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn) for btn in row] for row in buttons],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def direction_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["ЕГЭ", "ОГЭ", "Олимпиада"],
        ["1–4 класс", "5–6 класс"],
        ["7–8 класс", "9–10 класс"],
        ["11 класс"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn) for btn in row] for row in buttons],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def students_list_keyboard(students):
    buttons = []
    for student in students:
        name = (student.name or "").strip()
        surname = (student.surname or "").strip()
        full_name = f"{name} {surname}".strip()

        if full_name:
            buttons.append([
                InlineKeyboardButton(
                    text=full_name,
                    callback_data=f"student:{student.students_id}"
                )
            ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить ученика", callback_data="add_student")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def student_actions_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """
    Основное меню по работе с учеником.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Яндекс.Диск",       callback_data=f"yadisk:{student_id}")],
        [InlineKeyboardButton(text="📋 План",              callback_data=f"genplan:{student_id}")],
        [InlineKeyboardButton(text="📝 Задание",           callback_data=f"genassign:{student_id}")],
        [InlineKeyboardButton(text="📑 Домашка",           callback_data=f"genhomework:{student_id}")],
        [InlineKeyboardButton(text="🧪 Контрольная",       callback_data=f"genclasswork:{student_id}")],
        [InlineKeyboardButton(text="📑 Отчёты",            callback_data=f"reports:{student_id}")],
        [InlineKeyboardButton(text="📚 Материалы",         callback_data=f"genmaterials:{student_id}")],
        [InlineKeyboardButton(text="📎 Загрузить файл",    callback_data=f"upload:{student_id}")],
        [InlineKeyboardButton(text="📝 Проверить решение", callback_data=f"check_solution:{student_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать",      callback_data=f"edit_student:{student_id}")],
        [InlineKeyboardButton(text="💬 Чат с GPT",         callback_data=f"chat_gpt:{student_id}")],
        [InlineKeyboardButton(text="🗑 Удалить",           callback_data=f"delete_student:{student_id}")],
        [InlineKeyboardButton(text="📆 Дни занятий",       callback_data=f"edit_days:{student_id}")],
        [InlineKeyboardButton(text="🔙 Назад",              callback_data="back_students")]
    ])


def yandex_materials_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Домашка",        callback_data=f"upload_material:{student_id}:homework")],
        [InlineKeyboardButton(text="📝 Задание",        callback_data=f"upload_material:{student_id}:assignment")],
        [InlineKeyboardButton(text="📚 Теория",         callback_data=f"upload_material:{student_id}:theory")],
        [InlineKeyboardButton(text="📋 Учебный план",   callback_data=f"upload_material:{student_id}:plan")],
        [InlineKeyboardButton(text="🔙 Назад",          callback_data=f"student:{student_id}")]
    ])


def edit_student_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Имя",                 callback_data=f"edit_field:{student_id}:name")],
        [InlineKeyboardButton(text="Фамилия",             callback_data=f"edit_field:{student_id}:surname")],
        [InlineKeyboardButton(text="Класс",               callback_data=f"edit_field:{student_id}:class_")],
        [InlineKeyboardButton(text="Предмет",             callback_data=f"edit_field:{student_id}:subject")],
        [InlineKeyboardButton(text="Телефон",             callback_data=f"edit_field:{student_id}:phone")],
        [InlineKeyboardButton(text="Телефон родителя",    callback_data=f"edit_field:{student_id}:parent_phone")],
        [InlineKeyboardButton(text="Доп. инфо",           callback_data=f"edit_field:{student_id}:other_inf")],
        [InlineKeyboardButton(text="🔙 Назад",             callback_data=f"student:{student_id}")]
    ])


def confirm_generation_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для подтверждения результата генерации:
    ✅ Всё хорошо — добавляем в отчёт и на Яндекс.Диск
    ❌ Исправить  — переходим в режим ввода отзывов (await_generation_feedback)
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё хорошо", callback_data=f"confirm_yes:{student_id}"),
            InlineKeyboardButton(text="❌ Исправить",   callback_data=f"confirm_no:{student_id}")
        ]
    ])
