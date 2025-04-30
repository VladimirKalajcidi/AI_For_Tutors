from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import database.crud as crud

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        tg_id = None
        # Получаем Telegram ID пользователя из события
        if hasattr(event, "from_user") and event.from_user:
            tg_id = event.from_user.id
        elif hasattr(event, "message") and event.message and event.message.from_user:
            tg_id = event.message.from_user.id

        if tg_id is None:
            return await handler(event, data)

        # Ищем преподавателя по Telegram ID
        user = await crud.get_teacher_by_telegram_id(tg_id)
        # Добавляем teacher в data (None, если не найден)
        data["teacher"] = user if user else None

        return await handler(event, data)
