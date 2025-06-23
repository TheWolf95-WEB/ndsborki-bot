
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
import os
import asyncio

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
from telegram import ReplyKeyboardMarkup

load_dotenv(dotenv_path=".env")
configure_logging()

TOKEN = os.getenv("BOT_TOKEN")

# ✅ Главное меню
async def send_home_menu(app, exclude_id=None):
    menu = [["📋 Сборки Warzone"]]
    markup = ReplyKeyboardMarkup(menu, resize_keyboard=True, one_time_keyboard=False)
    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        admin_id = admin_id.strip()
        if not admin_id.isdigit():
            continue
        if exclude_id and int(admin_id) == exclude_id:
            continue
        try:
            await app.bot.send_message(
                chat_id=int(admin_id),
                text="✅ Бот перезапущен. Главное меню готово.",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения админу {admin_id}: {e}")

# ⏳ Запуск при старте
async def full_startup(app):
    print("🔧 Устанавливаю команды...")

    await clear_all_scopes(app)
    await set_commands(app)
    await asyncio.sleep(1)  # даём Telegram время принять команды

    user_id = await notify_restart(app)  # вернёт ID, если был рестарт
    await send_home_menu(app, exclude_id=user_id)


# 🔁 Создаём приложение
app = ApplicationBuilder().token(TOKEN).post_init(full_startup).build()

# Команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)

# Кнопки
app.add_handler(home_button)

# Админ
for h in admin_handlers:
    app.add_handler(h)

# Диалоги
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)

# Тест
app.add_handler(test_handler)

print("Бот запущен...")
app.run_polling()
