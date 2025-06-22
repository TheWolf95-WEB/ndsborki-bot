from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
import os
import logging

public_commands = [
    BotCommand("help", "📩 Помощь и поддержка"),
    BotCommand("add", "➕ Добавить сборку"),
    BotCommand("show_all", "📋 Все сборки"),
    BotCommand("home", "🏠 Главное меню"),
]

admin_commands = [
    BotCommand("restart", "🔁 Перезапустить бота"),
    BotCommand("update", "♻ Обновить и сбросить"),
    BotCommand("log", "🪵 Последние 30 строк логов"),
    BotCommand("status", "📊 Статистика и состояние"),
    BotCommand("check_files", "🗂 Проверка модулей"),
    BotCommand("delete", "❌ Удалить сборку"),
    BotCommand("stop_delete", "⛔ Остановить удаление"),
    *public_commands,
]

async def set_commands(app):
    try:
        await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
        await app.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())
        logging.info("✅ Обновлены публичные команды")
    except Exception as e:
        logging.warning(f"❌ Ошибка при установке публичных команд: {e}")

    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.strip().isdigit():
            try:
                chat_id = int(admin_id.strip())
                await app.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=chat_id))
                await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=chat_id))
                logging.info(f"✅ Обновлены команды для админа {chat_id}")
            except Exception as e:
                logging.warning(f"❌ Ошибка при установке команд для {admin_id}: {e}")
