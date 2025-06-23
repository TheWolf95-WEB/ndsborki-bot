from telegram import BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeChat
from telegram import BotCommand
import os
import logging


async def clear_all_scopes(app):
    await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
    await app.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    await app.bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())

    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.strip().isdigit():
            await app.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=int(admin_id)))

public_commands = [
    BotCommand("home", "🏠 Главное меню"),
    BotCommand("help", "📩 Помощь и поддержка"),
    BotCommand("show_all", "📋 Все сборки"),
    BotCommand("add", "➕ Добавить сборку"),
]

admin_commands = [
    BotCommand("restart", "🔁 Перезапустить бота"),
    *public_commands,
    BotCommand("log", "🪵 Последние 30 строк логов"),
    BotCommand("status", "📊 Статистика и состояние"),
    BotCommand("check_files", "🗂 Проверка модулей"),
    BotCommand("delete", "❌ Удалить сборку"),
    BotCommand("stop_delete", "⛔ Остановить удаление"),
]


async def set_commands(app):
    logging.warning("⚙ Установка команд запускается...")
    
    # Публичные команды
    try:
        await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
        await app.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())
        logging.warning("✅ Установлены публичные команды")
    except Exception as e:
        logging.error(f"❌ Ошибка установки публичных команд: {e}")

    # Команды для админов
    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.strip().isdigit():
            try:
                chat_id = int(admin_id.strip())
                await app.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=chat_id))
                await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=chat_id))
                logging.warning(f"✅ Установлены команды для админа: {chat_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка установки команд для админа {admin_id}: {e}")
        else:
            logging.warning(f"⚠️ Пропущен невалидный chat_id: {admin_id}")

    logging.warning("🎯 set_commands завершена.")

print('✅ Команды успешно установлены')
