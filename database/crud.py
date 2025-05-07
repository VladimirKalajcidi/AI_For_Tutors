from datetime import datetime, timedelta
from . import models
from .models import Student, Lesson
from database.db import async_session
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

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

async def update_teacher(teacher: models.Teacher):
    async with async_session() as session:
        session.add(teacher)
        await session.commit()

async def update_teacher_field(teacher: models.Teacher, field: str, value: str):
    async with async_session() as session:
        db_teacher = await session.get(models.Teacher, teacher.teacher_id)
        if db_teacher:
            setattr(db_teacher, field, value)
            await session.commit()
            # синхронизируем текущий объект
            setattr(teacher, field, value)



# ──────── STUDENT ────────

from .models import Student

async def create_student(
    session: AsyncSession,
    teacher_id: int,
    name: str,
    surname: str,
    class_: str,
    phone: str,
    parent_phone: str,
    subject: str,
    direction: str,
    other_inf: str
):
    """
    При создании нового ученика сразу инициализируем пустой отчёт и статистику токенов.
    """
    student = Student(
        teacher_id=teacher_id,
        name=name,
        surname=surname,
        class_=class_,
        phone=phone,
        parent_phone=parent_phone,
        subject=subject,
        direction=direction,
        other_inf=other_inf,
        report_student="",             # начальный текстовый отчёт
        prompt_tokens_total=0,
        completion_tokens_total=0
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return student


async def list_students(teacher: models.Teacher):
    async with async_session() as session:
        result = await session.execute(
            select(Student).where(Student.teacher_id == teacher.teacher_id)
        )
        return result.scalars().all()



from datetime import datetime
from sqlalchemy import select, func
from database.db import async_session
import database.models as models
import database.crud as crud

async def get_student_full_profile(teacher: models.Teacher, student_id: int):
    """
    Собирает подробный профиль ученика:
      - объект Student
      - последний структурированный отчёт (если есть таблица StudentReport)
      - количество пройденных занятий
      - список ближайших занятий
      - накопленный текстовый отчёт (report_student)
      - статистику по токенам
      - текущий счётчик генераций за месяц
    """
    async with async_session() as session:
        # 1) Ученика
        student = await session.get(Student, student_id)
        if not student or student.teacher_id != teacher.teacher_id:
            return None

        # 2) Последний структурированный (если есть модель StudentReport)
        try:
            from .models import StudentReport
            last_rep_q = await session.execute(
                select(StudentReport)
                .where(StudentReport.student_id == student_id)
                .order_by(StudentReport.created_at.desc())
                .limit(1)
            )
            last_rep = last_rep_q.scalars().first()
            progress   = last_rep.progress if last_rep else None
            next_topic = last_rep.next_topic if last_rep else None
        except ImportError:
            progress = None
            next_topic = None


        # 3) Пройденных занятий
        passed_q = await session.execute(
            select(func.count(Lesson.lesson_id))
            .where(Lesson.students_id == student_id, Lesson.passed == True)
        )
        passed_lessons = passed_q.scalar() or 0

        # 4) Ближайшие занятия
        upcoming_lessons = await list_upcoming_lessons(teacher)

        # 5) Текстовый отчёт
        report_text = student.report_student or ""

        # 6) Токены
        prompt_total     = getattr(student, "prompt_tokens_total", 0)    or 0
        completion_total = getattr(student, "completion_tokens_total", 0) or 0

        # 7) Счётчик генераций
        monthly_gen = student.monthly_gen_count or 0

        return {
            "student": student,
            "progress": progress,
            "next_topic": next_topic,
            "next_date": teacher.link_schedule,
            "passed_lessons": passed_lessons,
            "upcoming_lessons": upcoming_lessons,
            "report_text": report_text,
            "tokens_usage": {
                "prompt_total":     prompt_total,
                "completion_total": completion_total
            },
            "monthly_generation_count": monthly_gen
        }



async def list_subjects_from_students(teacher: models.Teacher):
    async with async_session() as session:
        result = await session.execute(
            select(Student.subject)
            .where(Student.teacher_id == teacher.teacher_id)
            .distinct()
        )
        return [row[0] for row in result.fetchall() if row[0]]

async def get_student(teacher: models.Teacher, student_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Student)
            .where(
                Student.teacher_id == teacher.teacher_id,
                Student.students_id == student_id
            )
        )
        return result.scalars().first()

async def update_student_field(teacher: models.Teacher, student_id: int, field: str, value: str):
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if student and student.teacher_id == teacher.teacher_id:
            setattr(student, field, value)
            await session.commit()

async def delete_student(teacher: models.Teacher, student_id: int):
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if student and student.teacher_id == teacher.teacher_id:
            await session.delete(student)
            await session.commit()



async def delete_teacher(teacher_id: int):
    """Удаляет преподавателя и всех его учеников из базы."""
    async with async_session() as session:
        teacher = await session.get(models.Teacher, teacher_id)
        if teacher:
            await session.delete(teacher)
            await session.commit()

async def list_upcoming_lessons_for_teacher(teacher_id: int) -> list[Lesson]:
    from datetime import date
    from sqlalchemy import select
    from database.db import async_session
    from database.models import Lesson

    today = date.today()
    async with async_session() as session:
        stmt = (
            select(Lesson)
            .where(
                Lesson.teacher_id == teacher_id,
                Lesson.passed == False,
                Lesson.data_of_lesson >= today
            )
            .order_by(Lesson.data_of_lesson, Lesson.start_time)
        )
        res = await session.execute(stmt)
        return res.scalars().all()


# ──────── Новые функции для токенов и текстового отчёта ────────

# database/crud.py

from database.db import async_session
from database.models import Student

async def add_token_usage(
    student_id: int,
    prompt_tokens: int,
    completion_tokens: int
) -> None:
    """
    Увеличивает глобальные счётчики токенов ученика.
    """
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if not student:
            # можно залогировать, но просто выходим
            return
        # складываем с тем, что уже было
        student.prompt_tokens_total     = (student.prompt_tokens_total     or 0) + prompt_tokens
        student.completion_tokens_total = (student.completion_tokens_total or 0) + completion_tokens
        session.add(student)
        await session.commit()


async def get_report_text(student_id: int) -> str:
    """
    Возвращает накопленный текстовый отчёт.
    """
    async with async_session() as session:
        student = await session.get(Student, student_id)
        return student.report_student if student else ""

async def set_report_text(student_id: int, text: str) -> bool:
    """
    Перезаписывает весь текстовый отчёт.
    """
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if not student:
            return False
        student.report_student = text
        session.add(student)
        await session.commit()
        return True

async def append_to_report(student_id: int, section: str, content: str) -> bool:
    """
    Дописать в отчёт новую секцию и, каждые 5 секций,
    пересуммировать его через GPT (generate_report_summary).
    """
    from services.gpt_service import generate_report_summary

    async with async_session() as session:
        student = await session.get(Student, student_id)
        if not student:
            return False

        # Добавляем новую секцию
        addition = f"\n\n=== {section} ===\n{content}"
        student.report_student = (student.report_student or "") + addition
        session.add(student)
        await session.commit()
        await session.refresh(student)

        # Если набралось кратно 5 секций — суммируем
        sections_count = student.report_student.count("=== ")
        if sections_count % 5 == 0:
            summary = await generate_report_summary(
                student=student,
                model=student.teacher.model,
                report_text=student.report_student
            )
            # Сохраняем обратно
            student.report_student = summary
            session.add(student)
            await session.commit()

        return True


async def mark_topic_completed(student_id: int) -> None:
    """
    Помечает очередную тему как пройденную (увеличивает lessons_completed).
    """
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if student:
            student.lessons_completed = (student.lessons_completed or 0) + 1
            session.add(student)
            await session.commit()


# ──────── LESSON ────────

from datetime import datetime
from database.db import async_session
import database.models as models


async def create_lesson(
    teacher: models.Teacher,
    student: Student,
    start_dt: datetime,
    end_dt: datetime,
    is_regular: bool = False,
    regular_interval: str = ""
) -> Lesson:
    async with async_session() as session:
        lesson = Lesson(
            teacher_id=teacher.teacher_id,
            students_id=student.students_id,
            data_of_lesson=start_dt.date(),
            start_time=start_dt.time(),
            end_time=end_dt.time(),
            passed=False,
            is_regular=is_regular,
            regular_interval=regular_interval
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        return lesson


async def list_upcoming_lessons(teacher: models.Teacher, from_time: datetime = None):
    if from_time is None:
        from_time = datetime.now()
    today = from_time.date()
    async with async_session() as session:
        result = await session.execute(
            select(Lesson)
            .where(Lesson.teacher_id == teacher.teacher_id)
            .where(Lesson.data_of_lesson >= today)
            .order_by(Lesson.data_of_lesson, Lesson.start_time)
        )
        return result.scalars().all()

async def get_lessons_for_notification(until_dt: datetime):
    async with async_session() as session:
        limit_date = until_dt.date()
        result = await session.execute(
            select(Lesson)
            .where(Lesson.data_of_lesson <= limit_date)
            .where(Lesson.passed == False)
        )
        return result.scalars().all()

async def set_lesson_notified(lesson_id: int):
    async with async_session() as session:
        lesson = await session.get(Lesson, lesson_id)
        if lesson:
            lesson.passed = True
            session.add(lesson)
            await session.commit()
        return lesson

async def get_lessons_for_teacher(teacher_id: int, start: datetime, end: datetime):
    async with async_session() as session:
        result = await session.execute(
            select(Lesson)
            .where(Lesson.teacher_id == teacher_id)
            .where(Lesson.data_of_lesson >= start.date())
            .where(Lesson.data_of_lesson <= end.date())
            .order_by(Lesson.data_of_lesson, Lesson.start_time)
        )
        return result.scalars().all()

async def delete_lesson(lesson_id: int) -> bool:
    async with async_session() as session:
        lesson = await session.get(Lesson, lesson_id)
        if lesson:
            await session.delete(lesson)
            await session.commit()
            return True
        return False

async def update_lesson_datetime(lesson_id: int, new_start: datetime, new_end: datetime):
    async with async_session() as session:
        lesson = await session.get(Lesson, lesson_id)
        if lesson:
            lesson.data_of_lesson = new_start.date()
            lesson.start_time      = new_start.time()
            lesson.end_time        = new_end.time()
            await session.commit()
            await session.refresh(lesson)
            return lesson
        return None
    
async def set_student_schedule_template(teacher, student_id: int, days: list[str], start_time, end_time):
    """
    Для регулярного расписания создаёт занятия на ближайшие даты по каждому дню недели.
    """
    async with async_session() as session:
        now = datetime.now()
        for day_abbr in days:
            idx = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].index(day_abbr)
            date_target = now + timedelta(days=(idx - now.weekday()) % 7)

            # Удаляем старую регулярку на эту дату
            await session.execute(
                delete(Lesson).where(
                    Lesson.students_id == student_id,
                    Lesson.is_regular  == True,
                    Lesson.data_of_lesson == date_target.date()
                )
            )
            # Добавляем новую
            sched = Lesson(
                teacher_id=teacher.teacher_id,
                students_id=student_id,
                data_of_lesson=date_target.date(),
                start_time=start_time,
                end_time=end_time,
                is_regular=True
            )
            session.add(sched)

        await session.commit()



async def delete_past_lessons():
    async with async_session() as session:
        today = datetime.now().date()
        await session.execute(
            delete(Lesson).where(Lesson.data_of_lesson < today)
        )
        await session.commit()

async def increment_generation_count(teacher: models.Teacher, student_id: int):
    """
    Сброс и инкремент счётчика генераций за месяц.
    """
    async with async_session() as session:
        student = await session.get(Student, student_id)
        if not student or student.teacher_id != teacher.teacher_id:
            return None
        current_month = datetime.now().strftime("%Y-%m")
        if student.generation_month != current_month:
            student.generation_month   = current_month
            student.monthly_gen_count  = 0
        student.monthly_gen_count = (student.monthly_gen_count or 0) + 1
        count = student.monthly_gen_count
        session.add(student)
        await session.commit()
        return count



# в database/crud.py

async def get_student_by_id_and_teacher(student_id: int, teacher_id: int):
    async with async_session() as session:
        stmt = select(models.Student).where(
            models.Student.students_id == student_id,
            models.Student.teacher_id   == teacher_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
