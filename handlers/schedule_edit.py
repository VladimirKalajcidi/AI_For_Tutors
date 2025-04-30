from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import hbold
from datetime import datetime, timedelta
from database import crud
from keyboards.schedule import lesson_action_kb, student_list_kb

router = Router()

class AddLessonFSM(StatesGroup):
    choosing_student = State()
    entering_date = State()
    entering_time = State()
    entering_duration = State()

class EditLessonFSM(StatesGroup):
    entering_date = State()
    entering_time = State()
    entering_duration = State()

# ─────────────────────── ДОБАВЛЕНИЕ ───────────────────────

@router.message(F.text == "➕ Добавить занятие")
async def add_lesson_start(message: Message, state: FSMContext, **data):
    teacher = data.get("teacher")
    # Проверка подписки
    now = datetime.now()
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < now:
        await message.answer("🔒 Подписка не активна. Продлите подписку, чтобы добавлять занятия.")
        return
    students = await crud.list_students(teacher)
    await state.set_state(AddLessonFSM.choosing_student)
    await state.update_data(teacher_id=teacher.teacher_id)

    
@router.callback_query(F.data.startswith("choose_student:"))
async def choose_student(callback: CallbackQuery, state: FSMContext):
    student_id = int(callback.data.split(":")[1])
    await state.update_data(student_id=student_id)
    await state.set_state(AddLessonFSM.entering_date)
    await callback.message.edit_text("📅 Введите дату занятия (в формате ДД.ММ.ГГГГ):")

@router.message(AddLessonFSM.entering_date)
async def enter_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        await state.update_data(date=date.isoformat())
        await state.set_state(AddLessonFSM.entering_time)
        await message.answer("🕒 Введите время начала (в формате ЧЧ:ММ):")
    except ValueError:
        await message.answer("⚠️ Неверный формат. Введите дату как 20.04.2025")

@router.message(AddLessonFSM.entering_time)
async def enter_time(message: Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text.strip(), "%H:%M").time()
        await state.update_data(start_time=time.strftime("%H:%M"))
        await state.set_state(AddLessonFSM.entering_duration)
        await message.answer("⏱ Укажите продолжительность занятия в минутах (например, 60):")
    except ValueError:
        await message.answer("⚠️ Неверный формат времени. Пример: 14:30")

@router.message(AddLessonFSM.entering_duration)
async def enter_duration(message: Message, state: FSMContext, **data):
    try:
        minutes = int(message.text.strip())
        info = await state.get_data()
        start_dt = datetime.strptime(f"{info['date']} {info['start_time']}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=minutes)

        teacher = data["teacher"]
        student = await crud.get_student(teacher, info["student_id"])

        lesson = await crud.create_lesson(teacher, student, student.subject, start_dt, end_dt)

        await message.answer(
            f"✅ Занятие добавлено:\n"
            f"📅 {start_dt.strftime('%d.%m')} с {start_dt.strftime('%H:%M')} до {end_dt.strftime('%H:%M')}\n"
            f"👤 {student.surname} {student.name} ({student.subject})"
        )
        await state.clear()
    except Exception as e:
        await message.answer("❌ Ошибка при создании занятия. Попробуйте снова.")
        print(e)

# ─────────────────────── УПРАВЛЕНИЕ ───────────────────────

@router.message(F.text == "📆 Мои занятия")
async def list_lessons(message: Message, **data):
    teacher = data.get("teacher")
    now = datetime.now()
    week_later = now + timedelta(days=7)
    lessons = await crud.get_lessons_for_teacher(teacher.teacher_id, now, week_later)
    if not lessons:
        await message.answer("📭 Занятий на ближайшую неделю нет.")
        return

    for lesson in lessons:
        start = datetime.strptime(lesson.data_of_lesson, "%Y-%m-%d %H:%M")
        end = datetime.strptime(lesson.end_time, "%Y-%m-%d %H:%M")
        student = await crud.get_student(teacher, lesson.students_id)
        student_name = f"{student.name} {student.surname}" if student else "—"
        text = (
            f"📘 Занятие:"
            f"👤 {student_name}"
            f"📅 {start.strftime('%d.%m')} с {start.strftime('%H:%M')} до {end.strftime('%H:%M')}"
        )
        await message.answer(text, reply_markup=lesson_action_kb(lesson.lesson_id))

@router.callback_query(F.data.startswith("edit_datetime_"))
async def callback_edit_lesson(callback: CallbackQuery, state: FSMContext):
    lesson_id = int(callback.data.split("_")[2])
    await callback.answer()
    await state.set_state(EditLessonFSM.entering_date)
    await state.update_data(lesson_id=lesson_id)
    await callback.message.edit_text("✏️ Введите новую дату (ДД.ММ.ГГГГ):")

@router.message(EditLessonFSM.entering_date)
async def edit_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        await state.update_data(date=date.isoformat())
        await state.set_state(EditLessonFSM.entering_time)
        await message.answer("🕒 Введите новое время начала (ЧЧ:ММ):")
    except Exception:
        await message.answer("❌ Неверный формат. Пример: 20.04.2025")

@router.message(EditLessonFSM.entering_time)
async def edit_time(message: Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text.strip(), "%H:%M").time()
        await state.update_data(start_time=time.strftime("%H:%M"))
        await state.set_state(EditLessonFSM.entering_duration)
        await message.answer("⏱ Введите продолжительность занятия в минутах:")
    except Exception:
        await message.answer("❌ Неверный формат времени. Пример: 14:30")

@router.message(EditLessonFSM.entering_duration)
async def edit_duration(message: Message, state: FSMContext):
    try:
        minutes = int(message.text.strip())
        data = await state.get_data()
        start = datetime.strptime(f"{data['date']} {data['start_time']}", "%Y-%m-%d %H:%M")
        end = start + timedelta(minutes=minutes)
        await crud.update_lesson_datetime(data['lesson_id'], start, end)
        await message.answer("✅ Время занятия обновлено!")
        await state.clear()
    except Exception:
        await message.answer("❌ Ошибка при сохранении времени занятия.")

@router.callback_query(F.data.startswith("cancel_lesson_"))
async def callback_cancel_lesson(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[2])
    await crud.delete_lesson(lesson_id)
    await callback.answer("🗑 Урок удалён")
    await callback.message.delete()

@router.callback_query(F.data.startswith("mark_done_"))
async def callback_mark_done(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[2])
    await crud.set_lesson_notified(lesson_id)
    await callback.answer("✅ Отмечено как проведённое")
    await callback.message.edit_reply_markup()
