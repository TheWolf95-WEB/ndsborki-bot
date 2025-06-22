# bot.py
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

load_dotenv()
configure_logging()

TOKEN = os.getenv("BOT_TOKEN")

app = ApplicationBuilder().token(TOKEN).post_init(home_cmd.on_startup).build()

# Команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)

# Админские
for h in admin_handlers:
    app.add_handler(h)

# Диалоги
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)

# Главное меню (кнопка)
app.add_handler(home_button)

app.run_polling()
