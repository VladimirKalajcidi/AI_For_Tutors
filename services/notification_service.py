import asyncio
import datetime
import database.crud as crud
import utils.helpers as helpers

async def start_scheduler(bot):
    # Periodically check for upcoming lessons and send reminders
    while True:
        now = datetime.datetime.now()
        from config import REMINDER_TIME_MINUTES
        cutoff = now + datetime.timedelta(minutes=REMINDER_TIME_MINUTES)
        lessons = await crud.get_lessons_for_notification(cutoff)
        for lesson in lessons:
            teacher = await crud.get_teacher_by_telegram_id(lesson.teacher_id)
            if not teacher:
                continue
            time_str = helpers.format_datetime(lesson.time, teacher.language)
            try:
                await bot.send_message(teacher.telegram_id, f"🔔 Reminder: Upcoming lesson at {time_str} with student {lesson.student.name}.")
            except Exception:
                pass
            await crud.set_lesson_notified(lesson.id)
        await asyncio.sleep(60)
