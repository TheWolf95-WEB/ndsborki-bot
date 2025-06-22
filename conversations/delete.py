import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)
from utils.permissions import ALLOWED_USERS
from utils.translators import load_translation_dict

DB_PATH = "database/builds.json"
DELETE_ENTER_ID, DELETE_CONFIRM_SIMPLE = range(130, 132)


async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return ConversationHandler.END

    if not os.path.exists(DB_PATH):
        await update.message.reply_text("❌ База сборок пуста.")
        return ConversationHandler.END

    with open(DB_PATH, 'r') as f:
        data = json.load(f)

    if not data:
        await update.message.reply_text("❌ Нет сборок для удаления.")
        return ConversationHandler.END

    context.user_data['delete_map'] = {}
    text_lines = ["🧾 Сборки для удаления:"]

    for idx, b in enumerate(data, start=1):
        context.user_data['delete_map'][str(idx)] = b
        translation = load_translation_dict(b.get("type", ""))
        modules = "\n".join(f"🔸 {k}: {translation.get(v, v)}" for k, v in b.get("modules", {}).items())
        text_lines.append(
            f"{b['weapon_name']} (ID {idx})\nТип: {b['type']}\n\nМодулей: {len(b['modules'])}\n{modules}\n\nАвтор: {b['author']}"
        )

    message = "\n\n".join(text_lines)
    keyboard = InlineKeyboardMarkup.from_button(InlineKeyboardButton("🚪 Выйти из удаления", callback_data="stop_delete"))

    await update.message.reply_text(
        message + "\n\nВведите ID сборки для удаления (например: 1)",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    return DELETE_ENTER_ID


async def stop_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text("🚫 Вы вышли из режима удаления.")
    return ConversationHandler.END


async def delete_enter_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    build_id = update.message.text.strip()
    if build_id not in context.user_data.get('delete_map', {}):
        await update.message.reply_text("❌ Неверный ID. Попробуйте снова.")
        return DELETE_ENTER_ID

    context.user_data['delete_id'] = build_id
    b = context.user_data['delete_map'][build_id]

    await update.message.reply_text(
        f"❗ Вы уверены, что хотите удалить сборку {b['weapon_name']} (ID: {build_id})?",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("Да", callback_data="confirm_delete")
        )
    )
    return DELETE_CONFIRM_SIMPLE


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    build_id = context.user_data.get('delete_id')
    if not build_id or build_id not in context.user_data.get('delete_map', {}):
        await update.message.reply_text("❌ Ошибка ID. Возврат к списку.")
        return await delete_start(update, context)

    to_delete = context.user_data['delete_map'][build_id]
    with open(DB_PATH, 'r') as f:
        data = json.load(f)

    new_data = [b for b in data if b != to_delete]
    with open(DB_PATH, 'w') as f:
        json.dump(new_data, f, indent=2)

    await update.callback_query.answer()
    await update.callback_query.message.edit_text("✅ Сборка удалена.")
    return await delete_start(update, context)


delete_conv = ConversationHandler(
    entry_points=[CommandHandler("delete", delete_start)],
    states={
        DELETE_ENTER_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, delete_enter_id),
        ],
        DELETE_CONFIRM_SIMPLE: [
            CallbackQueryHandler(delete_confirm, pattern="^confirm_delete$")
        ],
    },
    fallbacks=[],
)

stop_delete_callback = CallbackQueryHandler(stop_delete_callback, pattern="^stop_delete$")
