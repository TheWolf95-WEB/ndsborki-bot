import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from handlers.start import start_handler
from handlers.help import help_handler
from handlers.home import home_cmd, home_button

from handlers.show_all import (
    show_all_handler,
    showcat_callback,
    navigation_handler
)

from handlers.test import test_handler
from handlers.admin import admin_handlers
from conversations.view import view_conv
from conversations.add import add_conv
from conversations.delete import delete_conv, stop_delete_callback
from utils.logging_config import configure_logging
from utils.command_setup import set_commands, clear_all_scopes
from utils.keyboards import get_main_menu

load_dotenv(dotenv_path=".env")
configure_logging()
TOKEN = os.getenv("BOT_TOKEN")

async def on_startup(app):
    logging.info("Устанавливаю команды…")
    await clear_all_scopes(app)
    await set_commands(app)
    await asyncio.sleep(1)

    # Если был рестарт — уведомляем пользователя
    flag = "restart_message.txt"
    if os.path.exists(flag):
        with open(flag, encoding="utf-8") as f:
            user_id = int(f.read().strip())
        try:
            kb = get_main_menu(user_id)
            await app.bot.send_message(
                chat_id=user_id,
                text="✅ Бот успешно перезапущен.",
                reply_markup=kb
            )
        except Exception:
            logging.exception("Не удалось уведомить после рестарта")
        finally:
            os.remove(flag)

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .post_init(on_startup)
    .build()
)

# Регистрируем хэндлеры
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)
app.add_handler(home_button)
for h in admin_handlers:
    app.add_handler(h)
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)
app.add_handler(test_handler)

# Просмотр всех сборок Команда
app.add_handler(show_all_handler)
app.add_handler(showcat_callback)
app.add_handler(navigation_handler)

logging.info("Бот запущен…")
app.run_polling()
