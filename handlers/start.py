from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.keyboards import get_main_menu
from utils.permissions import ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    menu = get_main_menu(user_id)

    if user_id in ALLOWED_USERS:
        text = "Добро пожаловать в NDsborki BOT\n\n🛠 Админ: используйте команду /add для добавления сборок."
    else:
        text = (
            "👋 <b>Добро пожаловать в NDsborki BOT!</b>\n\n"
            "Здесь ты можешь:\n"
            " • Смотреть сборки оружия из Warzone\n"
            " • Выбирать тип и кол-во модулей для фильтра\n"
            " • Листать подходящие варианты с фото и автором\n\n"
            "📍 Жми <b>«Сборки Warzone»</b>, чтобы начать!\n\n"
            "⚠️ Добавление сборок доступно только администраторам.\n\n"
            "💬 Если есть идеи или нашёл баг — пиши @nd_admin95\n\n"
            "🛠 Бот будет постоянно обновляться и улучшаться!!"
        )

    await update.message.reply_text(text, reply_markup=menu, parse_mode="HTML")

start_handler = CommandHandler("start", start)
