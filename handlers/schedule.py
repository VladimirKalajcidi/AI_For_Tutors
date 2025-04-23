from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

import database.crud as crud
from states.schedule_states import ScheduleStates
import utils.helpers as helpers
from keyboards.schedule import lesson_action_kb

router = Router()

@router.message(Text(text=["📅 Расписание", "📅 Schedule"]))
async def menu_schedule(message: types.Message, teacher):
    lessons = await crud.list_upcoming_lessons(teacher)
    if not lessons:
        await message.answer("❌ У вас нет запланированных уроков на ближайшую неделю.")
        return

    text = "🗓 Ваше расписание на ближайшую неделю:\n"
    for les in lessons:
        start_str = helpers.format_datetime(les.data_of_lesson, teacher.language)
        end_str = helpers.format_datetime(les.end_time, teacher.language)
        student = await crud.get_student(teacher, les.students_id)
        student_name = f"{student.name} {student.surname}" if student else "(ученик удалён)"
        subject = student.subject if student else ""
        text += f"\n📚 {start_str} – {end_str} | {student_name} ({subject})"
    await message.answer(text)


@router.message(Command("add_lesson"))
async def cmd_add_lesson(message: types.Message, state: FSMContext, teacher):
    students = await crud.list_students(teacher)
    if not students:
        await message.answer("Нет учеников. Сначала добавьте ученика.")
        return

    text = "Выберите ученика для урока:\n"
    for idx, stud in enumerate(students, start=1):
        text += f"{idx}. {stud.name} {stud.surname} ({stud.subject})\n"
    text += "\nВведите номер ученика:"

    await state.set_state(ScheduleStates.choose_student)
    await state.update_data(students=[(stud.students_id, f"{stud.name} {stud.surname}") for stud in students])
    await message.answer(text)


@router.message(ScheduleStates.choose_student)
async def lesson_choose_student(message: types.Message, state: FSMContext, teacher):
    if not message.text.isdigit():
        await message.answer("Введите корректный номер ученика.")
        return
    choice = int(message.text)
    data = await state.get_data()
    students_list = data.get("students", [])
    if choice < 1 or choice > len(students_list):
        await message.answer(f"Неверный номер. Введите число от 1 до {len(students_list)}.")
        return
    student_id = students_list[choice - 1][0]
    await state.update_data(student_id=student_id)
    await state.set_state(ScheduleStates.enter_datetime)
    await message.answer("Введите дату и ВРЕМЯ начала урока в формате YYYY-MM-DD HH:MM:")


@router.message(ScheduleStates.enter_datetime)
async def lesson_enter_datetime(message: types.Message, state: FSMContext, teacher):
    try:
        start_time = datetime.fromisoformat(message.text.strip())
        await state.update_data(start_time=start_time)
        await state.set_state(ScheduleStates.enter_endtime)
        await message.answer("Теперь введите ВРЕМЯ окончания урока (например, 16:30):")
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте YYYY-MM-DD HH:MM")


@router.message(ScheduleStates.enter_endtime)
async def lesson_enter_endtime(message: types.Message, state: FSMContext, teacher):
    data = await state.get_data()
    start_time = data.get("start_time")
    try:
        hour, minute = map(int, message.text.strip().split(":"))
        end_time = start_time.replace(hour=hour, minute=minute)
        if end_time <= start_time:
            raise ValueError("End must be after start")
    except Exception:
        await message.answer("❌ Неверный формат времени окончания. Попробуйте HH:MM (например, 16:30)")
        return

    student_id = data.get("student_id")
    student = await crud.get_student(teacher, student_id)
    lesson = await crud.create_lesson(teacher, student, student.subject, start_time, end_time)

    start_str = helpers.format_datetime(start_time, teacher.language)
    end_str = helpers.format_datetime(end_time, teacher.language)
    await message.answer(f"✅ Урок запланирован: {start_str} – {end_str} с учеником {student.name}")
    await state.clear()
