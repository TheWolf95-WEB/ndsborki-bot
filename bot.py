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

load_dotenv()
configure_logging()

TOKEN = os.getenv("BOT_TOKEN")

# ⏳ Комбинируем запуск: уведомление при рестарте + главное меню
async def full_startup(app):
    await notify_restart(app)
    await home_cmd.on_startup(app)

# 🔁 Создаём приложение
app = ApplicationBuilder().token(TOKEN).post_init(full_startup).build()

# 📜 Основные команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)

# 🔐 Админ-команды
for h in admin_handlers:
    app.add_handler(h)

# 🤖 Диалоговые цепочки
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)

# 🏠 Кнопка "Главное меню"
app.add_handler(home_button)

# ▶️ Запуск бота
app.run_polling()
