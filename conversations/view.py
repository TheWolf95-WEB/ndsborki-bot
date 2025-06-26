import os
import json
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputFile
)
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
from utils.db import load_db, load_weapon_types
from utils.translators import load_translation_dict, get_type_label_by_key
from utils.permissions import admin_only

VIEW_CATEGORY_SELECT, VIEW_WEAPON, VIEW_SET_COUNT, VIEW_DISPLAY = range(4)

RAW_CATEGORIES = {
    "Топовая мета": "🔥 Топовая мета",
    "Мета":       "📈 Мета",
    "Новинки":    "🆕 Новинки"
}

@admin_only
async def view_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[lbl] for lbl in RAW_CATEGORIES.values()]
    await update.message.reply_text(
        "📁 Выберите категорию сборки:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return VIEW_CATEGORY_SELECT


async def view_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    category = next((k for k, lbl in RAW_CATEGORIES.items() if lbl == text), None)
    if not category:
        buttons = [[lbl] for lbl in RAW_CATEGORIES.values()]
        await update.message.reply_text(
            "❌ Пожалуйста, выберите категорию кнопкой.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return VIEW_CATEGORY_SELECT

    context.user_data['selected_category'] = category

    data = load_db()
    type_keys = sorted({
        b['type'] for b in data
        if b.get("mode", "").lower() == "warzone"
           and b.get("category") == category
    })
    if not type_keys:
        await update.message.reply_text(
            "⚠️ В этой категории ещё нет сборок.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    key_to_label = {wt['key']: wt['label'] for wt in load_weapon_types()}
    context.user_data['label_to_key'] = {lbl: k for k, lbl in key_to_label.items()}

    buttons = [[key_to_label.get(t, t)] for t in type_keys]
    await update.message.reply_text(
        "➡ Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return VIEW_WEAPON


async def view_select_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    type_key = context.user_data['label_to_key'].get(label)

    if type_key:
        context.user_data['selected_type'] = type_key
        weapon_list = sorted({
            b['weapon_name'] for b in load_db()
            if b['type'] == type_key and b.get('category') == context.user_data['selected_category']
        })

        if not weapon_list:
            await update.message.reply_text("⚠️ По этому типу нет оружия.")
            return ConversationHandler.END

        context.user_data['weapon_list'] = weapon_list
        buttons = [[w] for w in weapon_list]
        await update.message.reply_text(
            "🔫 Выберите оружие:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return VIEW_WEAPON

    weapon = label
    if weapon not in context.user_data.get('weapon_list', []):
        buttons = [[w] for w in context.user_data.get('weapon_list', [])]
        await update.message.reply_text(
            "❌ Пожалуйста, выберите оружие кнопкой.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )
        return VIEW_WEAPON

    context.user_data['selected_weapon'] = weapon

    data = load_db()
    c5 = sum(1 for b in data
             if b['weapon_name'] == weapon and b['type'] == context.user_data['selected_type'] and len(b['modules']) == 5)
    c8 = sum(1 for b in data
             if b['weapon_name'] == weapon and b['type'] == context.user_data['selected_type'] and len(b['modules']) == 8)

    buttons = [[f"5 ({c5})", f"8 ({c8})"]]
    await update.message.reply_text(
        "➡ Выберите количество модулей:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return VIEW_SET_COUNT


async def view_display_builds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        count = int(text.split()[0])
    except:
        await update.message.reply_text("⚠️ Нажмите на «5 (...)» или «8 (...)» кнопкой.")
        return VIEW_SET_COUNT

    filtered = [
        b for b in load_db()
        if b['type'] == context.user_data['selected_type']
           and b['weapon_name'] == context.user_data['selected_weapon']
           and len(b['modules']) == count
           and b.get('category') == context.user_data['selected_category']
    ]
    if not filtered:
        await update.message.reply_text("⚠️ К сожалению, сборок с таким количеством нет.")
        return await view_select_weapon(update, context)

    context.user_data['viewed_builds'] = filtered
    context.user_data['current_index'] = 0

    return await send_build(update, context)


async def send_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['current_index']
    build = context.user_data['viewed_builds'][idx]
    translation = load_translation_dict(build['type'])

    modules = "\n".join(
        f"├ {k}: {translation.get(v, v)}"
        for k, v in build['modules'].items()
    )
    caption = (
        f"📌 <b>Оружие:</b> {build['weapon_name']}\n"
        f"🎯 <b>Дистанция:</b> {build.get('role','-')}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(build['type'])}\n\n"
        f"🧩 <b>Модули:</b>\n{modules}\n\n"
        f"✍ <b>Автор:</b> {build['author']}"
    )

    nav = []
    row = []
    if idx > 0: row.append("⬅ Предыдущая")
    if idx < len(context.user_data['viewed_builds']) - 1:
        row.append("➡ Следующая")
    nav.append(row)
    nav.append(["📋 Сборки Warzone"])

    markup = ReplyKeyboardMarkup(nav, resize_keyboard=True)

    if os.path.exists(build.get('image', '')):
        with open(build['image'], 'rb') as f:
            await update.message.reply_photo(
                photo=InputFile(f),
                caption=caption,
                reply_markup=markup,
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=markup,
            parse_mode="HTML"
        )
    return VIEW_DISPLAY


async def next_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['current_index'] < len(context.user_data['viewed_builds']) - 1:
        context.user_data['current_index'] += 1
    return await send_build(update, context)


async def previous_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['current_index'] > 0:
        context.user_data['current_index'] -= 1
    return await send_build(update, context)


view_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📋 Сборки Warzone$"), view_start)],
    states={
        VIEW_CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_category_selected)],
        VIEW_WEAPON:          [MessageHandler(filters.TEXT & ~filters.COMMAND, view_select_weapon)],
        VIEW_SET_COUNT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, view_display_builds)],
        VIEW_DISPLAY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, view_display_builds),
            MessageHandler(filters.Regex("^➡ Следующая$"), next_build),
            MessageHandler(filters.Regex("^⬅ Предыдущая$"), previous_build),
            MessageHandler(filters.Regex("^📋 Сборки Warzone$"), view_start),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove()))]
)

__all__ = ["view_conv"]
