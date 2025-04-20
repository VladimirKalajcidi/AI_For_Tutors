from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from database import crud
from datetime import datetime, timedelta
import config

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_credentials_for_teacher(teacher):
    creds_data = {
        "token": teacher.google_access_token,
        "refresh_token": teacher.google_refresh_token,
        "token_uri": config.GOOGLE_TOKEN_URI,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "scopes": SCOPES
    }
    return Credentials.from_authorized_user_info(info=creds_data)

def get_calendar_service(teacher):
    creds = get_credentials_for_teacher(teacher)
    return build('calendar', 'v3', credentials=creds)

async def create_event(lesson):
    teacher = lesson.teacher
    service = get_calendar_service(teacher)

    event = {
        "summary": f"Занятие с {lesson.student.name}",
        "start": {
            "dateTime": lesson.time.isoformat(),
            "timeZone": "Europe/Moscow",
        },
        "end": {
            "dateTime": (lesson.time + timedelta(minutes=lesson.duration or 60)).isoformat(),
            "timeZone": "Europe/Moscow",
        },
        "description": lesson.topic or "Урок по предмету"
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event.get("id")

async def update_event(lesson_id: int, new_datetime: datetime):
    lesson = await crud.get_lesson_by_id(lesson_id)
    teacher = lesson.teacher
    if not lesson.google_event_id:
        return

    service = get_calendar_service(teacher)
    event = service.events().get(calendarId='primary', eventId=lesson.google_event_id).execute()

    start_time = new_datetime.isoformat()
    end_time = (new_datetime + timedelta(minutes=lesson.duration or 60)).isoformat()

    event['start']['dateTime'] = start_time
    event['end']['dateTime'] = end_time

    service.events().update(calendarId='primary', eventId=lesson.google_event_id, body=event).execute()

async def delete_event(lesson_id: int):
    lesson = await crud.get_lesson_by_id(lesson_id)
    teacher = lesson.teacher
    if not lesson.google_event_id:
        return

    service = get_calendar_service(teacher)
    service.events().delete(calendarId='primary', eventId=lesson.google_event_id).execute()