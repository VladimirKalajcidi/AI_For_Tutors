from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from datetime import date, timedelta, datetime

import database.crud as crud
from states.schedule_states import ScheduleStates
import utils.helpers as helpers

router = Router()

@router.message(Text(text=["📅 Расписание", "📅 Schedule"]))
async def menu_schedule(message: types.Message, teacher):
    # Проверяем подписку
    now = datetime.now()
    try:
        exp = datetime.fromisoformat(teacher.subscription_expires) if teacher.subscription_expires else None
    except Exception:
        exp = None
    if not exp or exp < now:
        await message.answer("🔒 Ваша подписка не активна. Продлите подписку, чтобы просматривать расписание.")
        return

    # Берём все будущие уроки и фильтруем по ближайшей неделе
    today      = date.today()
    week_later = today + timedelta(days=7)
    lessons    = await crud.list_upcoming_lessons_for_teacher(teacher.teacher_id)
    lessons    = [les for les in lessons
                  if today <= les.data_of_lesson <= week_later]

    if not lessons:
        await message.answer("У вас нет запланированных занятий на ближайшую неделю.")
        return

    text = "🗓 Ваше расписание на ближайшую неделю:\n"
    for les in lessons:
        dt_start = datetime.combine(les.data_of_lesson, les.start_time)
        dt_end   = datetime.combine(les.data_of_lesson, les.end_time)
        start_str = helpers.format_datetime(dt_start, teacher.language)
        end_str   = helpers.format_datetime(dt_end,   teacher.language)

        student = await crud.get_student(teacher, les.students_id)
        name    = f"{student.name} {student.surname}" if student else "(ученик удалён)"
        subj    = student.subject if student else ""
        text   += f"\n📚 {start_str} – {end_str} | {name} ({subj})"

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
    await state.update_data(students=[
        (stud.students_id, f"{stud.name} {stud.surname}") for stud in students
    ])
    await message.answer(text)


@router.message(ScheduleStates.choose_student)
async def lesson_choose_student(message: types.Message, state: FSMContext, teacher):
    if not message.text.isdigit():
        await message.answer("Введите корректный номер ученика.")
        return
    choice = int(message.text)
    data   = await state.get_data()
    roster = data.get("students", [])
    if choice < 1 or choice > len(roster):
        await message.answer(f"Неверный номер. Введите число от 1 до {len(roster)}.")
        return

    student_id = roster[choice - 1][0]
    await state.update_data(student_id=student_id)
    await state.set_state(ScheduleStates.enter_datetime)
    await message.answer("Введите дату и время начала урока в формате YYYY-MM-DD HH:MM:")


@router.message(ScheduleStates.enter_datetime)
async def lesson_enter_datetime(message: types.Message, state: FSMContext, teacher):
    try:
        start_dt = datetime.fromisoformat(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте YYYY-MM-DD HH:MM")
        return

    await state.update_data(start_dt=start_dt)
    await state.set_state(ScheduleStates.enter_endtime)
    await message.answer("Теперь введите время окончания урока в формате HH:MM:")


@router.message(ScheduleStates.enter_endtime)
async def lesson_enter_endtime(message: types.Message, state: FSMContext, teacher):
    data     = await state.get_data()
    start_dt = data.get("start_dt")
    try:
        hour, minute = map(int, message.text.strip().split(":"))
        end_dt = start_dt.replace(hour=hour, minute=minute)
        if end_dt <= start_dt:
            raise ValueError
    except Exception:
        await message.answer("❌ Неверный формат времени. Попробуйте HH:MM (например, 16:30)")
        return

    student = await crud.get_student(teacher, data["student_id"])
    # создаём урок (passed=False по умолчанию)
    lesson = await crud.create_lesson(
        teacher=teacher,
        student=student,
        start_dt=start_dt,
        end_dt=end_dt
    )

    start_str = helpers.format_datetime(start_dt, teacher.language)
    end_str   = helpers.format_datetime(end_dt,   teacher.language)
    await message.answer(f"✅ Урок запланирован: {start_str} – {end_str} с учеником {student.name}")
    await state.clear()
