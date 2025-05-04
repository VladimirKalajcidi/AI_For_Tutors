from aiogram import Router
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from keyboards.main_menu import main_menu_kb
from database.db import async_session
from keyboards.teachers import (
    teacher_profile_keyboard,
    edit_teacher_field_keyboard,
    settings_menu_keyboard
)
import database.crud as crud
from states.auth_state import TeacherStates
from database.models import Teacher

from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select


router = Router()

# 📌 Открытие меню настроек
@router.message(Text(text=["⚙️ Настройки"]))
async def menu_settings(message: Message, **data):
    await message.answer("⚙️ Настройки:", reply_markup=settings_menu_keyboard())

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
    # Показываем обновленный профиль
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


class YandexDiskStates(StatesGroup):
    waiting_for_token = State()


@router.callback_query(F.data == "link_yandex_disk")
async def start_yandex_token_input(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    instructions = (
        "🔐 *Подключение Яндекс.Диска*\n\n"
        "Чтобы подключить Яндекс.Диск и загружать туда материалы, выполните следующие шаги:\n\n"
        "Ты можешь прямо сейчас получить OAuth токен на сайте Яндекса:\n"
        "🔗 https://yandex.ru/dev/disk/poligon/ \n"
        "Перейди по ссылке.\n"
        "Нажми Получить OAuth-токен\n"
        "Авторизуйся под своей учёткой.\n"
        "Скопируй токен — и вставь в бота\n"
        "⚠️ Такой токен действителен до его отзыва вручную.\n"
    )

    await callback.message.answer(instructions, parse_mode="Markdown", disable_web_page_preview=True)
    await state.set_state(YandexDiskStates.waiting_for_token)


@router.message(YandexDiskStates.waiting_for_token)
async def save_yandex_token(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    token = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(Teacher).where(Teacher.telegram_id == teacher.telegram_id))
        db_teacher = result.scalar_one_or_none()

        if db_teacher:
            db_teacher.yandex_token = token
            await session.commit()
            await message.answer("✅ Токен Яндекс.Диска сохранён!")
        else:
            await message.answer("⚠️ Ошибка сохранения токена.")

    await state.clear()


from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext


# 🗑 Удаление аккаунта
@router.callback_query(Text("delete_account"))
async def callback_delete_account(callback: CallbackQuery):
    """Запрос подтверждения удаления аккаунта."""
    await callback.answer()
    confirm_kb = Message.reply_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_account")],
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_settings")]
    ])
    await callback.message.edit_text(
        "❗️ Вы уверены, что хотите удалить свой аккаунт? Это действие необратимо.",
        reply_markup=confirm_kb
    )

@router.callback_query(Text("confirm_delete_account"))
async def callback_confirm_delete_account(callback: CallbackQuery, teacher):
    """Полное удаление аккаунта преподавателя и связанных данных."""
    await crud.delete_teacher(teacher.teacher_id)
    await callback.answer("Ваш аккаунт удалён.", show_alert=True)
    # Завершаем диалог и информируем пользователя
    await callback.message.edit_text("Ваш аккаунт был успешно удалён. Спасибо, что воспользовались нашим сервисом!")