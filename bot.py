
import asyncio
import logging
import os
from dotenv import load_dotenv

from telegram.ext import ApplicationBuilder
from telegram import ReplyKeyboardMarkup
from handlers.start import start_handler
from handlers.help import help_handler
from handlers.home import home_cmd, home_button
from handlers.admin import admin_handlers
from handlers.test import test_handler
from conversations.view import view_conv
from conversations.add import add_conv
from conversations.delete import delete_conv, stop_delete_callback
from utils.logging_config import configure_logging
from utils.restart_notifier import notify_restart
from utils.command_setup import set_commands, clear_all_scopes

load_dotenv(dotenv_path=".env")
configure_logging()
TOKEN = os.getenv("BOT_TOKEN")

async def on_startup(app):
    print("🔧 Устанавливаю команды...")
    await clear_all_scopes(app)
    await set_commands(app)
    await asyncio.sleep(1)

    # Только инициатору рестарта
    await notify_restart(app)

app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

# Стандартные команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)
app.add_handler(home_button)

# Админ
for h in admin_handlers:
    app.add_handler(h)

# Диалоги
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)

# Отладка
app.add_handler(test_handler)

print("Бот запущен...")
app.run_polling()
