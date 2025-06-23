import os
import logging
from telegram import ReplyKeyboardMarkup

async def notify_restart(app):
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
