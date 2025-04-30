import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import config
from handlers import auth, subjects, students, schedule, settings, payment, schedule_edit, google_auth
from middlewares.auth_middleware import AuthMiddleware
from services import notification_service
from handlers import schedule_week  # подключаем обработчик недельного расписания

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Роутеры (handlers)
    dp.include_router(auth.router)
    dp.include_router(subjects.router)
    dp.include_router(students.router)
    dp.include_router(schedule.router)
    dp.include_router(settings.router)
    dp.include_router(payment.router)
    dp.include_router(schedule_edit.router)
    dp.include_router(google_auth.router)
    dp.include_router(schedule_week.router)

    # Мидлварь
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Устанавливаем команды бота (всплывающее меню)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="add_student", description="Добавить ученика"),
        BotCommand(command="add_lesson", description="Добавить урок"),
        BotCommand(command="login", description="Войти"),
        BotCommand(command="logout", description="Выйти"),
    ])
    # Инициализация таблиц БД
    from database import db
    await db.init_db()
    # Запуск фоновых уведомлений (напоминания о занятиях)
    asyncio.create_task(notification_service.start_scheduler(bot))
    # Запуск поллинга бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
