from aiogram import Router, types
from aiogram.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from database import crud
from states.schedule_states import ScheduleStates
import utils.helpers as helpers

router = Router()

def weekly_schedule_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить урок", callback_data="add_lesson_from_week")]
    ])

@router.message(Text(text=["📆 Расписание недели", "📆 Weekly Schedule"]))
async def weekly_schedule_view(message: types.Message, **data):
    teacher = data.get("teacher")
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=7)

    lessons = await crud.get_lessons_for_teacher(
        teacher_id=teacher.teacher_id,
        start=start_of_week,
        end=end_of_week
    )

    if not lessons:
        await message.answer("📭 У вас нет занятий на этой неделе.", reply_markup=weekly_schedule_kb())
        return

    # Группировка по дням
    day_map = {}
    for lesson in lessons:
        day_key = datetime.strptime(lesson.data_of_lesson, "%Y-%m-%d %H:%M").date()
        if day_key not in day_map:
            day_map[day_key] = []
        day_map[day_key].append(lesson)

    # Сортировка по дням недели
    sorted_days = sorted(day_map.keys())
    text = f"🗓 Ваше расписание на неделю:\n\n"
    for day in sorted_days:
        text += f"{day.strftime('%A, %d.%m')}\n"
        for lesson in sorted(day_map[day], key=lambda l: l.data_of_lesson):
            student = await crud.get_student(teacher, lesson.students_id)
            start_time = datetime.strptime(lesson.data_of_lesson, "%Y-%m-%d %H:%M").strftime("%H:%M")
            end_time = datetime.strptime(lesson.end_time, "%Y-%m-%d %H:%M").strftime("%H:%M")
            student_name = f"{student.name} {student.surname}" if student else "(ученик удалён)"
            subject = student.subject if student else ""
            text += f"▪️ {start_time}–{end_time} — {student_name} ({subject})\n"
        text += "\n"

    await message.answer(text, reply_markup=weekly_schedule_kb())

@router.callback_query(Text("add_lesson_from_week"))
async def handle_add_lesson_from_week(callback: types.CallbackQuery, state: FSMContext, **data):
    teacher = data.get("teacher")
    students = await crud.list_students(teacher)
    if not students:
        await callback.message.answer("Нет учеников. Сначала добавьте ученика.")
        return

    await callback.answer()
    await state.set_state(ScheduleStates.choose_student)
    await state.update_data(students=[(s.students_id, f"{s.name} {s.surname}") for s in students])

    text = "👤 Выберите ученика для урока:\n"
    for idx, stud in enumerate(students, start=1):
        text += f"{idx}. {stud.name} {stud.surname} ({stud.subject})\n"
    text += "\nВведите номер ученика:"
    await callback.message.answer(text)
