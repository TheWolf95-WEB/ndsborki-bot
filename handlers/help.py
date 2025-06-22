from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 Если у вас возникли вопросы, проблемы в работе бота или есть идеи по улучшению — не стесняйтесь, пишите прямо мне: @nd_admin95\n\n"
        "Я всегда на связи и стараюсь сделать бота ещё лучше для вас!"
    )

help_handler = CommandHandler("help", help_command)
