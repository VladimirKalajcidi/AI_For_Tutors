from datetime import datetime

def format_datetime(dt: datetime, language: str = "en") -> str:
    if language == "ru":
        return dt.strftime("%d.%m.%Y %H:%M")
    else:
        return dt.strftime("%Y-%m-%d %H:%M")
