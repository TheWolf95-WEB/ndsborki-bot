
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
from utils.command_setup import set_commands, clear_all_scopes

load_dotenv(dotenv_path=".env")
configure_logging()
TOKEN = os.getenv("BOT_TOKEN")

async def on_startup(app):
    print("🔧 Устанавливаю команды...")

    await clear_all_scopes(app)
    await set_commands(app)
    await asyncio.sleep(1)

    # Прямо здесь обрабатываем рестарт
    if os.path.exists("restart_message.txt"):
        with open("restart_message.txt", "r") as f:
            user_id = int(f.read().strip())
        try:
            menu = [["📋 Сборки Warzone"]]
            markup = ReplyKeyboardMarkup(menu, resize_keyboard=True)
            await app.bot.send_message(
                chat_id=user_id,
                text="✅ Бот успешно перезапущен. Возвращаюсь в главное меню...",
                reply_markup=markup
            )
        except Exception as e:
            print(f"❌ Не удалось отправить сообщение после рестарта: {e}")
        os.remove("restart_message.txt")

app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

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

print("Бот запущен...")
app.run_polling()
