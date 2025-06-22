from telegram import BotCommand

public_commands = [
    BotCommand("help", "📩 Помощь и поддержка"),
    BotCommand("add", "➕ Добавить сборку"),
    BotCommand("show_all", "📋 Все сборки"),
    BotCommand("home", "🏠 Главное меню"),
]

admin_commands = [
    BotCommand("restart", "🔁 Перезапустить бота"),
    BotCommand("log", "🪵 Последние 30 строк логов"),
    BotCommand("status", "📊 Статистика и состояние"),
    BotCommand("check_files", "🗂 Проверка модулей"),
    BotCommand("delete", "❌ Удалить сборку"),
    BotCommand("stop_delete", "⛔ Остановить удаление"),
    *public_commands
]

async def set_commands(app):
    await app.bot.set_my_commands(public_commands)
    
    for admin_id in os.getenv("ALLOWED_USERS", "").split(","):
        if admin_id.isdigit():
            await app.bot.set_my_commands(
                admin_commands,
                scope={"type": "chat", "chat_id": int(admin_id)}
            )
