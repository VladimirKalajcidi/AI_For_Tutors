from aiogram import Router, types
from aiogram.filters import Command, Text

import database.crud as crud
from keyboards.main_menu import get_main_menu

router = Router()

@router.message(Text(text=["Предметы", "Subjects"]))
async def menu_subjects(message: types.Message, teacher):
    subjects = await crud.list_subjects_from_students(teacher)
    if not subjects:
        await message.answer("❌ Предметы не найдены. Чтобы добавить новый, укажите его при создании или редактировании ученика.")
    else:
        text = "📚 Ваши предметы:\n" + "\n".join(f"- {sub}" for sub in subjects)
        await message.answer(text)
    # Добавление новых предметов происходит через профиль ученика

@router.message(Command("add_subject"))
async def cmd_add_subject(message: types.Message):
    await message.answer(
        "⚠️ Добавление отдельных предметов не требуется.\n"
        "Укажите предмет прямо в профиле ученика при создании или редактировании."
    )
