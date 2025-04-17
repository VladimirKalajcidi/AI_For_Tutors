from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database.crud as crud
from states.schedule_states import ScheduleStates
import utils.helpers as helpers

router = Router()

@router.message(Text(text=["📅 Расписание", "📅 Schedule"]))
async def menu_schedule(message: types.Message, teacher):
    lessons = await crud.list_upcoming_lessons(teacher)
    if not lessons:
        await message.answer("No upcoming lessons.")
    else:
        text = "Upcoming lessons:\n"
        for les in lessons:
            dt_str = helpers.format_datetime(les.time, teacher.language)
            # Get student and subject names
            student = await crud.get_student(teacher, les.student_id)
            sub_name = ""
            if student and student.subject:
                sub_name = student.subject.name
            text += f"{dt_str} - {student.name if student else ''} ({sub_name})\n"
        await message.answer(text)
    await message.answer("To add a lesson, use /add_lesson.")

@router.message(Command("add_lesson"))
async def cmd_add_lesson(message: types.Message, state: FSMContext, teacher):
    students = await crud.list_students(teacher)
    if not students:
        await message.answer("No students available. Add a student first.")
        return
    text = "Select a student for the lesson:\n"
    for idx, stud in enumerate(students, start=1):
        text += f"{idx}. {stud.name} ({stud.subject.name if stud.subject else ''})\n"
    text += "Enter the number of the student:"
    await state.set_state(ScheduleStates.choose_student)
    await state.update_data(students=[(stud.id, stud.name) for stud in students])
    await message.answer(text)

@router.message(ScheduleStates.choose_student)
async def lesson_choose_student(message: types.Message, state: FSMContext, teacher):
    if not message.text.isdigit():
        await message.answer("Please enter a valid number.")
        return
    choice = int(message.text)
    data = await state.get_data()
    students_list = data.get("students", [])
    if choice < 1 or choice > len(students_list):
        await message.answer(f"Number out of range. Enter a number from 1 to {len(students_list)}.")
        return
    student_id = students_list[choice-1][0]
    await state.update_data(student_id=student_id)
    await state.set_state(ScheduleStates.enter_datetime)
    await message.answer("Enter date and time for the lesson (format YYYY-MM-DD HH:MM):")

@router.message(ScheduleStates.enter_datetime)
async def lesson_enter_datetime(message: types.Message, state: FSMContext, teacher):
    text = message.text.strip()
    try:
        lesson_time = datetime.fromisoformat(text)
    except Exception:
        await message.answer("❌ Invalid datetime format. Please use YYYY-MM-DD HH:MM.")
        return
    data = await state.get_data()
    student_id = data.get("student_id")
    student = await crud.get_student(teacher, student_id)
    subject = student.subject if student else None
    new_lesson = await crud.create_lesson(teacher, student, subject, lesson_time)
    dt_str = helpers.format_datetime(new_lesson.time, teacher.language)
    await message.answer(f"✅ Lesson scheduled on {dt_str} with {student.name}.")
    await state.clear()
