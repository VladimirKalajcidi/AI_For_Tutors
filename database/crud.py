from datetime import datetime
from sqlalchemy import select
from . import db, models
from database.models import Teacher
from database.db import async_session
from sqlalchemy import select, delete, desc
from database.models import Lesson

# ──────── TEACHER ────────

async def get_teacher_by_login(login: str):
    async with async_session() as session:
        result = await session.execute(select(models.Teacher).filter_by(login=login))
        return result.scalars().first()

async def get_teacher_by_telegram_id(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(models.Teacher).filter_by(telegram_id=telegram_id))
        return result.scalars().first()

async def get_teacher_by_id(teacher_id: int):
    async with async_session() as session:
        result = await session.execute(select(models.Teacher).filter_by(teacher_id=teacher_id))
        return result.scalars().first()

async def create_teacher(login: str, password_hash: str, telegram_id: int, name: str = "", language: str = "ru"):
    async with async_session() as session:
        teacher = models.Teacher(
            login=login,
            password_hash=password_hash,
            telegram_id=telegram_id,
            name=name,
            language=language,
            subscription_expires=None,
            is_logged_in=True
        )
        session.add(teacher)
        await session.commit()
        await session.refresh(teacher)
        return teacher

async def update_teacher(teacher: Teacher):
    async with async_session() as session:
        session.add(teacher)
        await session.commit()

async def update_teacher_field(teacher, field: str, value: str):
    async with async_session() as session:
        db_teacher = await session.get(models.Teacher, teacher.teacher_id)
        if db_teacher:
            setattr(db_teacher, field, value)
            await session.commit()
            setattr(teacher, field, value)  # обновим локально

# ──────── STUDENT ────────

async def create_student(
    teacher,
    name: str,
    surname: str,
    class_: str,
    subject: str,
    phone: str,
    parent_phone: str,
    other_inf: str = ""
):
    async with async_session() as session:
        student = models.Student(
            name=name,
            surname=surname,
            class_=class_,
            subject=subject,
            teacher_id=teacher.teacher_id,
            phone=phone,
            parent_phone=parent_phone,
            other_inf=other_inf,
        )
        session.add(student)
        await session.commit()
        await session.refresh(student)
        return student

async def list_students(teacher):
    async with async_session() as session:
        result = await session.execute(select(models.Student).where(models.Student.teacher_id == teacher.teacher_id))
        return result.scalars().all()

async def get_student_full_profile(teacher, student_id):
    async with async_session() as session:
        student = await session.get(models.Student, student_id)
        if not student or student.teacher_id != teacher.teacher_id:
            return None

        last_report = await session.execute(
            select(models.StudentReport)
            .where(models.StudentReport.student_id == student_id)
            .order_by(models.StudentReport.created_at.desc())
            .limit(1)
        )
        last_report = last_report.scalars().first()
        return {
            "student": student,
            "progress": last_report.progress if last_report else None,
            "next_topic": last_report.next_topic if last_report else None,
            "next_date": teacher.link_schedule
        }

async def get_student(teacher, student_id):
    async with async_session() as session:
        result = await session.execute(
            select(models.Student).where(
                models.Student.teacher_id == teacher.teacher_id,
                models.Student.students_id == student_id
            )
        )
        return result.scalar_one_or_none()

async def list_subjects_from_students(teacher: models.Teacher):
    async with async_session() as session:
        result = await session.execute(
            select(models.Student.subject)
            .where(models.Student.teacher_id == teacher.teacher_id)
            .distinct()
        )
        return [row[0] for row in result.fetchall() if row[0]]

async def update_student_field(teacher, student_id, field: str, value: str):
    async with async_session() as session:
        student = await session.get(models.Student, student_id)
        if student and student.teacher_id == teacher.teacher_id:
            setattr(student, field, value)
            await session.commit()

async def delete_student(teacher, student_id):
    async with async_session() as session:
        student = await session.get(models.Student, student_id)
        if student and student.teacher_id == teacher.teacher_id:
            await session.delete(student)
            await session.commit()

# ──────── LESSON ────────

from datetime import datetime

async def create_lesson(teacher: models.Teacher, student: models.Student, subject: str, start_time: datetime, end_time: datetime, title: str = ""):
    async with async_session() as session:
        lesson = models.Lesson(
            teacher_id=teacher.teacher_id,
            students_id=student.students_id,
            data_of_lesson=start_time.date(),
            start_time=start_time.time(),
            end_time=end_time.time(),
            passed=False,
            link_plan="",
            link_report="",
            link_test="",
            link_test_verified="",
            link_HW="",
            link_HW_verified=""
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        return lesson


async def list_upcoming_lessons(teacher: models.Teacher, from_time: datetime = None):
    async with async_session() as session:
        if from_time is None:
            from_time = datetime.now()
        result = await session.execute(
            select(models.Lesson)
            .where(models.Lesson.teacher_id == teacher.teacher_id)
            .where(models.Lesson.data_of_lesson >= from_time.strftime("%Y-%m-%d %H:%M"))
            .order_by(models.Lesson.data_of_lesson)
        )
        return result.scalars().all()

async def get_lessons_for_notification(until_time: datetime):
    async with async_session() as session:
        result = await session.execute(
            select(models.Lesson)
            .where(models.Lesson.data_of_lesson <= until_time.strftime("%Y-%m-%d %H:%M"))
            .where(models.Lesson.passed == False)
        )
        return result.scalars().all()

async def set_lesson_notified(lesson_id: int):
    async with async_session() as session:
        result = await session.execute(select(models.Lesson).filter_by(lesson_id=lesson_id))
        lesson = result.scalars().first()
        if lesson:
            lesson.passed = True
            session.add(lesson)
            await session.commit()
        return lesson

async def get_lessons_for_teacher(teacher_id: int, start: datetime, end: datetime):
    async with async_session() as session:
        result = await session.execute(
            select(models.Lesson)
            .where(models.Lesson.teacher_id == teacher_id)
            .where(models.Lesson.data_of_lesson >= start.date())
            .where(models.Lesson.data_of_lesson <= end.date())
            .order_by(models.Lesson.data_of_lesson, models.Lesson.start_time)
        )
        return result.scalars().all()


async def delete_lesson(lesson_id: int):
    async with async_session() as session:
        lesson = await session.get(models.Lesson, lesson_id)
        if lesson:
            await session.delete(lesson)
            await session.commit()
            return True
        return False

async def update_lesson_datetime(lesson_id: int, new_start: datetime, new_end: datetime):
    async with async_session() as session:
        lesson = await session.get(models.Lesson, lesson_id)
        if lesson:
            lesson.data_of_lesson = new_start.strftime("%Y-%m-%d %H:%M")
            lesson.end_time = new_end.strftime("%Y-%m-%d %H:%M")
            await session.commit()
            return lesson
        return None
    
async def set_student_schedule_template(teacher, student_id, days, start_time, end_time):
    from datetime import datetime, timedelta

    async with async_session() as session:
        now = datetime.now()

        for day_abbr in days:
            # Определим индекс дня недели и ближайшую дату
            weekday_index = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].index(day_abbr)
            date_target = now + timedelta(days=(weekday_index - now.weekday()) % 7)

            # Удалим только старые уроки на этот день
            await session.execute(
                delete(Lesson).where(
                    Lesson.students_id == student_id,
                    Lesson.is_regular == True,
                    Lesson.data_of_lesson == date_target.date()
                )
            )

            # Добавим новое занятие
            schedule = Lesson(
                teacher_id=teacher.teacher_id,
                students_id=student_id,
                data_of_lesson=date_target.date(),
                start_time=start_time,
                end_time=end_time,
                is_regular=True
            )
            session.add(schedule)

        await session.commit()


