from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
import os

from handlers.start import start_handler
from handlers.help import help_handler
from handlers.home import home_cmd, home_button
from handlers.admin import admin_handlers
from conversations.view import view_conv
from conversations.add import add_conv
from conversations.delete import delete_conv, stop_delete_callback

from utils.logging_config import configure_logging
from utils.restart_notifier import notify_restart
from utils.command_setup import set_commands
from telegram import ReplyKeyboardMarkup

load_dotenv()
configure_logging()

TOKEN = os.getenv("BOT_TOKEN")

# ✅ Показ главного меню
async def send_home_menu(app):
    menu = [["📋 Сборки Warzone"]]
    markup = ReplyKeyboardMarkup(menu, resize_keyboard=True)
    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.strip().isdigit():
            await app.bot.send_message(
                chat_id=int(admin_id),
                text="✅ Бот перезапущен. Главное меню готово.",
                reply_markup=markup
            )

# ⏳ Запуск при старте
async def full_startup(app):
    await notify_restart(app)
    await set_commands(app)
    await send_home_menu(app)

# 🔁 Создаём приложение
app = ApplicationBuilder().token(TOKEN).post_init(full_startup).build()

# 📜 Основные команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)

# 🔐 Админ-команды
for h in admin_handlers:
    app.add_handler(h)

# 🤖 Диалоги
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)

# 🏠 Главное меню
app.add_handler(home_button)

# ▶️ Запуск
app.run_polling()
