import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import config
from handlers import auth, subjects, students, schedule, settings, payment
from middlewares.auth_middleware import AuthMiddleware
from services import notification_service

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    # Include routers
    dp.include_router(auth.router)
    dp.include_router(subjects.router)
    dp.include_router(students.router)
    dp.include_router(schedule.router)
    dp.include_router(settings.router)
    dp.include_router(payment.router)
    # Middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    # Set bot commands (for menu hints)
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="add_subject", description="Add a subject"),
        BotCommand(command="add_student", description="Add a student"),
        BotCommand(command="add_lesson", description="Add a lesson"),
        BotCommand(command="login", description="Log in"),
        BotCommand(command="logout", description="Log out"),
    ])
    # Initialize database tables
    from database import db
    await db.init_db()
    # Start background notification service
    asyncio.create_task(notification_service.start_scheduler(bot))
    # Run bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
