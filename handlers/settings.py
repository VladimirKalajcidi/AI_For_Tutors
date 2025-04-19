from aiogram import Router
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from keyboards.main_menu import get_main_menu
from keyboards.teachers import (
    teacher_profile_keyboard,
    edit_teacher_field_keyboard,
    settings_menu_keyboard
)
import database.crud as crud
from states.auth_state import TeacherStates

router = Router()

# 📌 Открытие меню настроек
@router.message(Text(text=["⚙️ Настройки"]))
async def menu_settings(message: Message, **data):
    await message.answer("⚙️ Настройки:", reply_markup=settings_menu_keyboard())


# 🌐 Смена языка
@router.callback_query(Text("set_lang"))
async def callback_set_lang(callback: CallbackQuery, teacher):
    await callback.answer()
    new_lang = "en" if teacher.language == "ru" else "ru"
    teacher.language = new_lang
    await crud.update_teacher(teacher)
    await callback.message.edit_text(f"Language changed to {'English' if new_lang == 'en' else 'Russian'}.")
    await callback.message.answer("Main menu:", reply_markup=get_main_menu(new_lang))


# ✏️ Редактирование профиля — список полей
@router.callback_query(Text("edit_profile"))
async def callback_edit_profile(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("✏️ Что вы хотите изменить?", reply_markup=edit_teacher_field_keyboard())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# Выбор поля для редактирования
@router.callback_query(Text(startswith="edit_teacher_field:"))
async def callback_select_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    await state.set_state(TeacherStates.editing_field)
    await state.update_data(edit_field=field)
    await callback.answer()
    await callback.message.edit_text(f"✏️ Введите новое значение для: *{field}*", parse_mode="Markdown")


# Обработка ввода нового значения
@router.message(TeacherStates.editing_field)
async def process_edit_field(message: Message, state: FSMContext, teacher):
    state_data = await state.get_data()
    field = state_data.get("edit_field")

    if not field:
        return

    new_value = message.text.strip()
    await crud.update_teacher_field(teacher, field, new_value)
    await state.clear()

    await message.answer(f"✅ Поле *{field}* успешно обновлено!", parse_mode="Markdown")

    profile_text = (
        f"👤 {teacher.surname or ''} {teacher.name or ''} {teacher.patronymic or ''}\n"
        f"🗓️ Дата рождения: {teacher.birth_date or '—'}\n"
        f"📞 Телефон: {teacher.phone or '—'}\n"
        f"📧 Email: {teacher.email or '—'}\n"
        f"📚 Предметы: {teacher.subjects or '—'}\n"
        f"💼 Профессия: {teacher.occupation or '—'}\n"
        f"🏢 Место работы: {teacher.workplace or '—'}"
    )

    await message.answer(profile_text, reply_markup=teacher_profile_keyboard())


# 🔙 Кнопка "Назад" из редактирования в настройки
@router.callback_query(Text("back_to_settings"))
async def back_to_settings(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("⚙️ Настройки:", reply_markup=settings_menu_keyboard())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
