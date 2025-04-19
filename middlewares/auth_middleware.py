from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import database.crud as crud


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        tg_id = None

        # Получаем telegram_id пользователя из разных типов событий
        if hasattr(event, "from_user") and event.from_user:
            tg_id = event.from_user.id
        elif hasattr(event, "message") and event.message and event.message.from_user:
            tg_id = event.message.from_user.id

        if tg_id is None:
            return await handler(event, data)

        # Получаем преподавателя по Telegram ID
        user = await crud.get_teacher_by_telegram_id(tg_id)

        # Добавляем teacher в data
        if user:
            print(f"[middleware] Found teacher: {user.name}")
            data["teacher"] = user
        else:
            print("[middleware] No teacher found!")
            data["teacher"] = None

        return await handler(event, data)
