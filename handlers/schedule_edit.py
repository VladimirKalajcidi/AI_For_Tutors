from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from database import crud
from utils.helpers import parse_datetime_input
from services.calendar_service import update_event, delete_event
from keyboards.common import confirm_cancel_kb
from keyboards.schedule import lesson_action_kb
from datetime import datetime

router = Router()

class EditLessonState(StatesGroup):
    waiting_for_new_datetime = State()
    confirm_cancel = State()

@router.callback_query(F.data.startswith("lesson_edit_"))
async def start_edit_lesson(callback: CallbackQuery, state: FSMContext):
    lesson_id = int(callback.data.split("_")[-1])
    await state.update_data(lesson_id=lesson_id)
    
    await callback.message.edit_text(
        "Что вы хотите сделать с занятием?",
        reply_markup=lesson_action_kb(lesson_id)
    )

@router.callback_query(F.data.startswith("edit_datetime_"))
async def ask_new_datetime(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую дату и время в формате: 20.04.2025 15:00")
    await state.set_state(EditLessonState.waiting_for_new_datetime)

@router.message(EditLessonState.waiting_for_new_datetime)
async def process_new_datetime(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lesson_id = data["lesson_id"]

    new_dt = parse_datetime_input(message.text)
    if not new_dt:
        await message.answer("❌ Неверный формат. Попробуйте снова в формате: 20.04.2025 15:00")
        return

    await crud.update_lesson_datetime(lesson_id, new_dt)
    await update_event(lesson_id, new_dt)  # обновление в Google Calendar

    await message.answer(f"✅ Занятие перенесено на {new_dt.strftime('%d.%m.%Y %H:%M')}")
    await state.clear()

@router.callback_query(F.data.startswith("cancel_lesson_"))
async def confirm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditLessonState.confirm_cancel)
    await callback.message.edit_text("Вы уверены, что хотите отменить занятие?", reply_markup=confirm_cancel_kb())

@router.callback_query(EditLessonState.confirm_cancel, F.data == "confirm_yes")
async def cancel_lesson(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lesson_id = data["lesson_id"]

    await crud.delete_lesson(lesson_id)
    await delete_event(lesson_id)  # удаление из Google Calendar

    await callback.message.edit_text("❌ Занятие отменено")
    await state.clear()

@router.callback_query(EditLessonState.confirm_cancel, F.data == "confirm_no")
async def cancel_abort(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Операция отменена")
    await state.clear()
