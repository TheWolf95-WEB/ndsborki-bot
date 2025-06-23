import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

ALLOWED_USERS = list(map(int, os.getenv("ALLOWED_USERS", "").split(",")))

def admin_only(func):
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("❌ У тебя нет прав для этой команды.")
            return
        return await func(update, context)
    return wrapper
