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


def student_actions_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Яндекс.Диск", callback_data=f"yadisk:{student_id}")],
        [InlineKeyboardButton(text="📋 План", callback_data=f"genplan:{student_id}")],
        [InlineKeyboardButton(text="📝 Задание", callback_data=f"genassign:{student_id}")],
        [InlineKeyboardButton(text="📑 Домашка", callback_data=f"genhomework:{student_id}")],
        [InlineKeyboardButton(text="🧪 Контрольная", callback_data=f"genclasswork:{student_id}")],
        [InlineKeyboardButton(text="📑 Отчёты", callback_data=f"reports:{student_id}")],
        [InlineKeyboardButton(text="📎 Материалы", callback_data=f"genmaterials:{student_id}")],
        [InlineKeyboardButton(text="📤 Отправить файл", callback_data=f"upload:{student_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student:{student_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_student:{student_id}")],

        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_students")]
    ])

def yandex_materials_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Домашка", callback_data=f"upload_material:{student_id}:homework")],
        [InlineKeyboardButton(text="📝 Задание", callback_data=f"upload_material:{student_id}:assignment")],
        [InlineKeyboardButton(text="📚 Теория", callback_data=f"upload_material:{student_id}:theory")],
        [InlineKeyboardButton(text="📋 Учебный план", callback_data=f"upload_material:{student_id}:plan")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"student:{student_id}")]
    ])

def edit_student_keyboard(student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data=f"edit_field:{student_id}:name")],
        [InlineKeyboardButton(text="Фамилия", callback_data=f"edit_field:{student_id}:surname")],
        [InlineKeyboardButton(text="Класс", callback_data=f"edit_field:{student_id}:class_")],
        [InlineKeyboardButton(text="Предмет", callback_data=f"edit_field:{student_id}:subject")],
        [InlineKeyboardButton(text="Телефон", callback_data=f"edit_field:{student_id}:phone")],
        [InlineKeyboardButton(text="Телефон родителя", callback_data=f"edit_field:{student_id}:parent_phone")],
        [InlineKeyboardButton(text="Доп. инфо", callback_data=f"edit_field:{student_id}:other_inf")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"student:{student_id}")]
    ])


