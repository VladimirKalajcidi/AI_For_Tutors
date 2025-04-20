import os
from dotenv import load_dotenv

load_dotenv()  # load environment variables from a .env file if present

# Telegram Bot API token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Database URL for SQLAlchemy (using SQLite file)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///tutor_bot.db")

# OpenAI API key for GPT integration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
#OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
PROXYAPI_KEY = os.getenv("PROXYAPI_KEY", "sk-0rh9j7yU0H94x7jFJKzeLNMV2Ld1wZKx")

# Yandex Disk OAuth token (if using a single account for storage; otherwise each teacher will have their own token)
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN", "")

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-client-secret"


# YooKassa API credentials for subscription payments
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

# Subscription parameters
SUBSCRIPTION_DURATION_DAYS = int(os.getenv("SUBSCRIPTION_DURATION_DAYS", "30"))

# Reminder time for lesson notifications (minutes before lesson to send notification)
REMINDER_TIME_MINUTES = int(os.getenv("REMINDER_TIME_MINUTES", "60"))
