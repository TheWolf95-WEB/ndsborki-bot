import os
import logging
from telegram import ReplyKeyboardMarkup

async def notify_restart(app):
    if os.path.exists("restart_message.txt"):
        try:
            with open("restart_message.txt", "r") as f:
                user_id = int(f.read().strip())

            menu = [['📋 Сборки Warzone']]
            if str(user_id) in os.getenv("ALLOWED_USERS", "").split(","):
                menu.append(['➕ Добавить сборку'])

            markup = ReplyKeyboardMarkup(menu, resize_keyboard=True)

            await app.bot.send_message(
                chat_id=user_id,
                text="✅ Бот успешно перезапущен. Возвращаюсь в главное меню...",
                reply_markup=markup,
                parse_mode="HTML"
            )

            os.remove("restart_message.txt")
        except Exception:
            logging.exception("❌ Не удалось отправить сообщение после рестарта")
