import os
from dotenv import load_dotenv

load_dotenv()  # загружаем переменные окружения из .env, если есть

# Telegram Bot API токен
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# URL базы данных для SQLAlchemy (по умолчанию SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///tutor_bot.db")

# OpenAI API ключ для интеграции с GPT
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
#OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROXYAPI_KEY = os.getenv("PROXYAPI_KEY", "")

# OAuth токен Яндекс.Диска (если используется один глобальный аккаунт; иначе у каждого преподавателя свой токен)
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN", "")

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-client-secret"

# Реквизиты YooKassa API для приема оплаты подписки
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

# Параметры подписки
SUBSCRIPTION_DURATION_DAYS = int(os.getenv("SUBSCRIPTION_DURATION_DAYS", "30"))

# Время перед занятием для напоминания (в минутах)
REMINDER_TIME_MINUTES = int(os.getenv("REMINDER_TIME_MINUTES", "60"))

# Telegram ID администратора (для подтверждения оплаты)
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "1313788984"))
