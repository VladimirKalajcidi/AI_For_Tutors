from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import database.crud as crud

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        tg_id = None
        # Determine user ID from message or callback events
        if hasattr(event, "from_user") and event.from_user:
            tg_id = event.from_user.id
        elif hasattr(event, "message") and event.message and event.message.from_user:
            tg_id = event.message.from_user.id
        if tg_id is None:
            return await handler(event, data)
        user = await crud.get_teacher_by_telegram_id(tg_id)
        if user and user.is_logged_in:
            data["teacher"] = user
        else:
            data["teacher"] = None
        return await handler(event, data)
