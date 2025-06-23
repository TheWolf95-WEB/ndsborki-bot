import os
from dotenv import load_dotenv

# Надёжно грузим .env
load_dotenv(dotenv_path=".env")

# Получаем ALLOWED_USERS как список int, игнорируя пустые значения
raw_users = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(uid) for uid in raw_users.split(",") if uid.strip().isdigit()]

def admin_only(func):
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ У тебя нет прав для этой команды.")
            return
        return await func(update, context)
    return wrapper
