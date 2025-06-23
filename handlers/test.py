from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def testcommands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmds = await context.bot.get_my_commands()
    if not cmds:
        await update.message.reply_text("❌ Команды не установлены.")
    else:
        msg = "📋 Текущие команды Telegram:\n"
        msg += "\n".join([f"/{cmd.command} — {cmd.description}" for cmd in cmds])
        await update.message.reply_text(msg)

test_handler = CommandHandler("testcommands", testcommands)
