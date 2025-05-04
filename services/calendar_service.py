from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from database import crud
from datetime import datetime
import config

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_credentials_for_teacher(teacher):
    creds_data = {
        "token": teacher.google_access_token,
        "refresh_token": teacher.google_refresh_token,
        "token_uri":   config.GOOGLE_TOKEN_URI,
        "client_id":   config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "scopes":      SCOPES
    }
    return Credentials.from_authorized_user_info(info=creds_data)

def get_calendar_service(teacher):
    creds = get_credentials_for_teacher(teacher)
    return build('calendar', 'v3', credentials=creds)

async def create_event(lesson):
    teacher = lesson.teacher
    service = get_calendar_service(teacher)

    # собираем ISO-строки из даты + времени
    start_dt = datetime.combine(lesson.data_of_lesson, lesson.start_time)
    end_dt   = datetime.combine(lesson.data_of_lesson, lesson.end_time)

    event = {
        "summary": f"Урок с {lesson.student.name}",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Europe/Moscow",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Europe/Moscow",
        },
        "description": lesson.topic or "Урок по предмету"
    }
    created = service.events().insert(calendarId='primary', body=event).execute()
    # сохраняем google_event_id в БД, если нужно
    await crud.set_lesson_google_event_id(lesson.lesson_id, created["id"])
    return created["id"]

async def update_event(lesson_id: int, new_start: datetime, new_end: datetime):
    lesson = await crud.get_lesson_by_id(lesson_id)
    teacher = lesson.teacher
    if not lesson.google_event_id:
        return

    service = get_calendar_service(teacher)
    event   = service.events().get(
        calendarId='primary',
        eventId=lesson.google_event_id
    ).execute()

    event['start']['dateTime'] = new_start.isoformat()
    event['end']['dateTime']   = new_end.isoformat()
    service.events().update(
        calendarId='primary',
        eventId=lesson.google_event_id,
        body=event
    ).execute()

async def delete_event(lesson_id: int):
    lesson = await crud.get_lesson_by_id(lesson_id)
    teacher = lesson.teacher
    if not lesson.google_event_id:
        return
    service = get_calendar_service(teacher)
    service.events().delete(
        calendarId='primary',
        eventId=lesson.google_event_id
    ).execute()
    # сбросим в БД
    await crud.set_lesson_google_event_id(lesson_id, None)
