from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_google_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("calendar", "v3", credentials=creds)
    return service

async def create_event(lesson):
    service = get_google_service()
    event = {
        "summary": f"Lesson with {lesson.student.name}",
        "start": {
            "dateTime": lesson.time.isoformat(),
            "timeZone": "Europe/Moscow",
        },
        "end": {
            "dateTime": (lesson.time + timedelta(minutes=60)).isoformat(),
            "timeZone": "Europe/Moscow",
        },
    }
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event["id"]

async def update_event(lesson):
    pass  # аналогично create_event, но с использованием .update()

async def delete_event(lesson):
    pass  # вызвать .delete(calendarId='primary', eventId=...)
