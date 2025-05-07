import asyncio
import datetime
import database.crud as crud
import utils.helpers as helpers
from services.auto_schedule_service import generate_weekly_lessons

async def start_scheduler(bot):
    while True:
        now = datetime.datetime.now()

        # Автогенерация уроков один раз в день
        if now.hour == 6 and now.minute == 0:
            try:
                await generate_weekly_lessons()
            except Exception as e:
                print(f"Ошибка автогенерации уроков: {e}")

        from config import REMINDER_TIME_MINUTES
        cutoff = now + datetime.timedelta(minutes=REMINDER_TIME_MINUTES)
        lessons = await crud.get_lessons_for_notification(cutoff)

        for lesson in lessons:
            # 🔁 Заменяем ленивые обращения к связанным объектам на явные
            teacher = await crud.get_teacher_by_id(lesson.teacher_id)
            student = await crud.get_student_by_id_and_teacher(lesson.students_id, lesson.teacher_id)

            if not teacher or not student:
                continue

            time_str = helpers.format_datetime(lesson.start_time, teacher.language)

            try:
                await bot.send_message(
                    teacher.telegram_id,
                    f"🔔 Напоминание: скоро урок в {time_str} с учеником {student.name}."
                )
            except Exception:
                pass

            await crud.set_lesson_notified(lesson.lesson_id)

        await asyncio.sleep(60)
