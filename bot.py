
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

load_dotenv()
configure_logging()

TOKEN = os.getenv("BOT_TOKEN")

# ✅ Показ главного меню
async def send_home_menu(app):
    menu = [["📋 Сборки Warzone"]]
    markup = ReplyKeyboardMarkup(menu, resize_keyboard=True, one_time_keyboard=False)
    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.strip().isdigit():
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

    await notify_restart(app)
    await clear_all_scopes(app)
    await set_commands(app)

    # ✅ Проверка: выводим текущие команды Telegram
    try:
        cmds = await app.bot.get_my_commands()
        print("📋 Текущие команды Telegram:")
        for cmd in cmds:
            print(f"   /{cmd.command} — {cmd.description}")
    except Exception as e:
        print(f"❌ Ошибка при получении команд: {e}")

    await send_home_menu(app)


# 🔁 Создаём приложение
app = ApplicationBuilder().token(TOKEN).post_init(lambda app: asyncio.create_task(full_startup(app))).build()

# 1. Сначала добавляем команды
app.add_handler(start_handler)
app.add_handler(help_handler)
app.add_handler(home_cmd)

# 2. Затем обработчики кнопок
app.add_handler(home_button)

# 3. Потом админ-команды
for h in admin_handlers:
    app.add_handler(h)

# 4. В самом конце добавляем диалоги (conversations)
app.add_handler(view_conv)
app.add_handler(add_conv)
app.add_handler(delete_conv)
app.add_handler(stop_delete_callback)


app.add_handler(test_handler)


# ▶️ Запуск
print("Бот запущен...")
app.run_polling()
