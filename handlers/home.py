from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters
from handlers.start import start

# Команда /home
async def home_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🏠 Главное меню...")
    await start(update, context)

# Кнопка «🏠 Главное меню»
home_cmd = CommandHandler("home", home_command)
home_button = MessageHandler(filters.Regex("🏠 Главное меню"), home_command)
