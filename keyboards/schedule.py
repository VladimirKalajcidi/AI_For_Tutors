from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def lesson_action_kb(lesson_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_datetime_{lesson_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_lesson_{lesson_id}")],
        [InlineKeyboardButton(text="✔️ Проведено", callback_data=f"mark_done_{lesson_id}")]
    ])

def student_list_kb(students):
    buttons = [
        [InlineKeyboardButton(text=f"{s.name} {s.surname}", callback_data=f"select_schedule_student:{s.students_id}")]
        for s in students
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
