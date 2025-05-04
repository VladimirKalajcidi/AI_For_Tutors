import json
from datetime import datetime, timedelta, time, date
from sqlalchemy import select
from database.db import async_session
from database.models import Student, Lesson
from database import crud

# дни недели в .strftime("%a") формате
WEEKDAYS = {"Mon","Tue","Wed","Thu","Fri","Sat","Sun"}
DEFAULT_TIME     = "15:00"
DEFAULT_DURATION = 60  # минут

async def generate_weekly_lessons():
    async with async_session() as session:
        # получаем всех студентов вместе с учителем
        result   = await session.execute(select(Student).join(Student.teacher))
        students = result.scalars().all()

    today        = date.today()
    next_week    = [ today + timedelta(days=i) for i in range(7) ]
    default_h, default_m = map(int, DEFAULT_TIME.split(":"))

    for student in students:
        if not student.schedule_days:
            continue
        try:
            days = set(json.loads(student.schedule_days))
        except json.JSONDecodeError:
            continue

        teacher = student.teacher

        for day in next_week:
            if day.strftime("%a") not in days:
                continue

            # если уже есть урок на эту дату и для этого студента — пропускаем
            existing = await crud.list_upcoming_lessons_for_teacher(teacher.teacher_id)
            if any(
                les.students_id == student.students_id and
                les.data_of_lesson == day
                for les in existing
            ):
                continue

            start_dt = datetime.combine(day, time(default_h, default_m))
            end_dt   = start_dt + timedelta(minutes=DEFAULT_DURATION)
            # создаём урок
            await crud.create_lesson(teacher, student, start_dt, end_dt)
            # (не забудьте также создавать событие в календаре и уведомление)
            print(f"[AutoSchedule] Урок для {student.name} на {day.isoformat()} в {DEFAULT_TIME}")
