from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def students_list_keyboard(students):
    buttons = []
    for student in students:
        name = (student.name or "").strip()
        surname = (student.surname or "").strip()
        full_name = f"{name} {surname}".strip()

        if full_name:  # только если есть имя
            buttons.append([
                InlineKeyboardButton(
                    text=full_name,
                    callback_data=f"student:{student.students_id}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Add Student", callback_data="add_student")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def student_actions_keyboard(student_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Generate Plan", callback_data=f"genplan:{student_id}"),
            InlineKeyboardButton(text="📄 Generate Assignment", callback_data=f"genassign:{student_id}")
        ],
        [
            InlineKeyboardButton(text="📎 Upload File", callback_data=f"upload:{student_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_students")
        ]
    ])


def student_actions_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 План", callback_data=f"genplan:{student_id}")],
        [InlineKeyboardButton(text="📝 Задание", callback_data=f"genassign:{student_id}")],
        [InlineKeyboardButton(text="📑 Отчёты", callback_data=f"reports:{student_id}")],
        [InlineKeyboardButton(text="📎 Материалы", callback_data=f"materials:{student_id}")],
        [InlineKeyboardButton(text="📤 Отправить файл", callback_data=f"upload:{student_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_students")]
    ])

