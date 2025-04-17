from aiogram import Router, types
from aiogram.filters import Command, Text

import database.crud as crud
from keyboards.main_menu import get_main_menu

router = Router()


@router.message(Text(text=["Предметы", "Subjects"]))
async def menu_subjects(message: types.Message, teacher):
    subjects = await crud.list_subjects_from_students(teacher)
    if not subjects:
        await message.answer("No subjects found. Use /add_subject НазваниеПредмета to add one.")
    else:
        text = "📚 Your subjects:\n" + "\n".join(f"- {sub}" for sub in subjects)
        await message.answer(text)
    await message.answer("To add a new subject, just assign it to a student.")


@router.message(Command("add_subject"))
async def cmd_add_subject(message: types.Message):
    await message.answer(
        "⚠️ Subjects are now just text fields attached to students.\n"
        "To 'add' a subject, assign it directly when creating or editing a student."
    )
