from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import config
from database import crud

router = Router()

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleAuthState(StatesGroup):
    waiting_for_code = State()

@router.message(F.text.lower() == "подключить google")
async def start_google_auth(message: Message, state: FSMContext):
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )
    auth_url, _ = flow.authorization_url(prompt="consent")

    await state.set_state(GoogleAuthState.waiting_for_code)
    await state.update_data(flow_json=flow.to_json())

    await message.answer(f"Перейдите по ссылке, авторизуйтесь и вставьте код сюда:\n{auth_url}")

@router.message(GoogleAuthState.waiting_for_code)
async def finish_google_auth(message: Message, state: FSMContext):
    data = await state.get_data()
    flow = InstalledAppFlow.from_client_config(
        json.loads(data["flow_json"])["client_config"],
        scopes=SCOPES
    )
    flow.fetch_token(code=message.text.strip())

    creds = flow.credentials

    teacher = await crud.get_teacher_by_telegram_id(message.from_user.id)
    if teacher:
        teacher.google_access_token = creds.token
        teacher.google_refresh_token = creds.refresh_token
        await crud.update_teacher(teacher)

        await message.answer("✅ Google Calendar успешно подключён!")
    else:
        await message.answer("❌ Не удалось найти ваш профиль преподавателя.")

    await state.clear()
