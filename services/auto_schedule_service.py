import json
from datetime import datetime, timedelta
from sqlalchemy import select
from database.db import async_session
from database.models import Student, Teacher
from database import crud

WEEKDAYS = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}

DEFAULT_TIME = "15:00"
DEFAULT_DURATION = 60

async def generate_weekly_lessons():
    async with async_session() as session:
        result = await session.execute(select(Student).join(Teacher))
        students = result.scalars().all()

        today = datetime.now().date()
        upcoming_days = [today + timedelta(days=i) for i in range(7)]

        for student in students:
            if not student.schedule_days:
                continue

            try:
                days = json.loads(student.schedule_days)
            except json.JSONDecodeError:
                continue

            teacher = student.teacher

            for day in upcoming_days:
                if day.strftime("%a") in days:
                    start_time = datetime.combine(day, datetime.strptime(DEFAULT_TIME, "%H:%M").time())
                    end_time = start_time + timedelta(minutes=DEFAULT_DURATION)

                    existing_lessons = await crud.get_lessons_for_teacher(
                        teacher.teacher_id,
                        start_time,
                        end_time
                    )

                    already_exists = any(
                        lesson.students_id == student.students_id and lesson.data_of_lesson[:10] == day.isoformat()
                        for lesson in existing_lessons
                    )

                    if not already_exists:
                        await crud.create_lesson(teacher, student, student.subject, start_time, end_time)
                        print(f"Создан урок для {student.name} в {start_time.strftime('%d.%m')} в {DEFAULT_TIME}")
