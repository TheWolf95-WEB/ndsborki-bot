import json
import logging
import pathlib

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from utils.db import load_db, load_weapon_types, get_type_label_by_key
from utils.translators import load_translation_dict
from utils.permissions import admin_only

# Состояния диалога
VIEW_CATEGORY_SELECT, VIEW_WEAPON, VIEW_SET_COUNT, VIEW_DISPLAY = range(4)

# Категории
RAW_CATEGORIES = {
    "Топовая мета": "🔥 Топовая мета",
    "Мета":       "📈 Мета",
    "Новинки":    "🆕 Новинки",
}


@admin_only
async def view_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(lbl, callback_data=f"cat|{key}")]
        for key, lbl in RAW_CATEGORIES.items()
    ]
    await update.message.reply_text(
        "📁 Выберите категорию сборки:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return VIEW_CATEGORY_SELECT


async def on_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, category = query.data.split("|", 1)
    context.user_data["selected_category"] = category

    data = load_db()
    type_keys = sorted({
        b["type"] for b in data
        if b.get("mode", "").lower() == "warzone"
           and b.get("category") == category
    })
    if not type_keys:
        return await query.edit_message_text("⚠️ Нет сборок в этой категории.")

    key_to_label = {wt["key"]: wt["label"] for wt in load_weapon_types()}
    buttons = [
        [InlineKeyboardButton(key_to_label.get(k, k), callback_data=f"type|{k}")]
        for k in type_keys
    ]
    # возвращаем на шаг КАТЕГОРИИ
    buttons.append([InlineKeyboardButton("⬅ Назад к категориям", callback_data="restart")])

    await query.edit_message_text(
        f"📁 <b>Категория:</b> {RAW_CATEGORIES[category]}\n➡ Выберите тип оружия:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )
    return VIEW_WEAPON


async def on_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, type_key = query.data.split("|", 1)
    context.user_data["selected_type"] = type_key
    category = context.user_data["selected_category"]

    weapon_list = sorted({
        b["weapon_name"] for b in load_db()
        if b["type"] == type_key and b.get("category") == category
    })
    if not weapon_list:
        return await query.edit_message_text("⚠️ По этому типу нет оружия.")

    buttons = [
        [InlineKeyboardButton(w, callback_data=f"weapon|{w}")]
        for w in weapon_list
    ]
    # возвращаем на шаг ТИПЫ
    buttons.append([InlineKeyboardButton("⬅ Назад к типам", callback_data="back_type")])

    await query.edit_message_text(
        f"📁 <b>Категория:</b> {RAW_CATEGORIES[category]}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(type_key)}\n\n"
        "➡ Выберите оружие:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )
    return VIEW_SET_COUNT


async def on_weapon_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, weapon = query.data.split("|", 1)
    context.user_data["selected_weapon"] = weapon

    category = context.user_data["selected_category"]
    type_key = context.user_data["selected_type"]
    data = load_db()

    c5 = sum(1 for b in data
             if b["weapon_name"] == weapon
                and b["type"] == type_key
                and len(b["modules"]) == 5
                and b.get("category") == category)
    c8 = sum(1 for b in data
             if b["weapon_name"] == weapon
                and b["type"] == type_key
                and len(b["modules"]) == 8
                and b.get("category") == category)

    buttons = [[
        InlineKeyboardButton(f"5 модулей ({c5})", callback_data="view|5|0"),
        InlineKeyboardButton(f"8 модулей ({c8})", callback_data="view|8|0"),
    ]]
    # возвращаем на шаг ОРУЖИЕ
    buttons.append([InlineKeyboardButton("⬅ Назад к оружию", callback_data="back_weapon")])

    await query.edit_message_text(
        f"📁 <b>Категория:</b> {RAW_CATEGORIES[category]}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(type_key)}\n"
        f"⚔️ <b>Оружие:</b> {weapon}\n\n"
        "➡ Выберите количество модулей:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )
    return VIEW_DISPLAY


async def on_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вывод сборки и навигация «Пред / След».
    """
    query = update.callback_query
    await query.answer()
    _, count_str, idx_str = query.data.split("|")
    count, idx = int(count_str), int(idx_str)

    category = context.user_data["selected_category"]
    type_key = context.user_data["selected_type"]
    weapon = context.user_data["selected_weapon"]

    filtered = [
        b for b in load_db()
        if b["type"] == type_key
           and b["weapon_name"] == weapon
           and len(b["modules"]) == count
           and b.get("category") == category
    ]
    if not filtered:
        return await query.edit_message_text("⚠️ Сборок с таким количеством нет.")

    idx %= len(filtered)
    context.user_data["viewed_builds"] = filtered
    context.user_data["current_index"] = idx

    build = filtered[idx]
    tr = load_translation_dict(type_key)
    modules = "\n".join(f"├ {k}: {tr.get(v, v)}" for k, v in build["modules"].items())
    caption = (
        f"📌 <b>Оружие:</b> {build['weapon_name']}\n"
        f"🎯 <b>Роль:</b> {build.get('role','-')}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(type_key)}\n\n"
        f"🧩 <b>Модули ({count}):</b>\n{modules}\n\n"
        f"✍ <b>Автор:</b> {build['author']}"
    )

    # Первая строка: Предыдущая и Следующая
    nav1 = []
    if len(filtered) > 1:
        prev_idx = (idx - 1) % len(filtered)
        next_idx = (idx + 1) % len(filtered)
        nav1 = [
            InlineKeyboardButton("⬅ Предыдущая", callback_data=f"view|{count}|{prev_idx}"),
            InlineKeyboardButton("Следующая ➡", callback_data=f"view|{count}|{next_idx}")
        ]

    # Вторая строка: Назад к выбору модулей и Категории
    nav2 = [
        InlineKeyboardButton("⬅ Назад", callback_data="back_count"),
        InlineKeyboardButton("📋 Категории", callback_data="restart")
    ]

    markup = InlineKeyboardMarkup([nav1, nav2])

    img = build.get("image")
    if img and pathlib.Path(img).exists():
        media = InputMediaPhoto(open(img, "rb"), caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=markup)
    else:
        await query.edit_message_text(caption, reply_markup=markup, parse_mode="HTML")

    return VIEW_DISPLAY


# Хэндлеры «Назад»
async def on_back_to_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    query.data = f"cat|{context.user_data['selected_category']}"
    return await on_category_selected(update, context)

async def on_back_to_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    query.data = f"type|{context.user_data['selected_type']}"
    return await on_type_selected(update, context)

async def on_back_to_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    query.data = f"weapon|{context.user_data['selected_weapon']}"
    return await on_weapon_selected(update, context)

async def on_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await view_start(update, context)


# Регистрируем ConversationHandler
view_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^📋 Сборки Warzone$"), view_start),
    ],
    states={
        VIEW_CATEGORY_SELECT: [
            CallbackQueryHandler(on_category_selected, pattern="^cat\\|")
        ],
        VIEW_WEAPON: [
            CallbackQueryHandler(on_type_selected, pattern="^type\\|"),
            CallbackQueryHandler(on_restart,    pattern="^restart$"),
        ],
        VIEW_SET_COUNT: [
            CallbackQueryHandler(on_weapon_selected, pattern="^weapon\\|"),
            CallbackQueryHandler(on_back_to_type,    pattern="^back_type$"),
        ],
        VIEW_DISPLAY: [
            CallbackQueryHandler(on_view_callback,    pattern="^view\\|"),
            CallbackQueryHandler(on_back_to_weapon,   pattern="^back_weapon$"),
            CallbackQueryHandler(on_back_to_count,    pattern="^back_count$"),
            CallbackQueryHandler(on_restart,          pattern="^restart$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: u.callback_query.message.reply_text(
            "❌ Отменено.", reply_markup=None
        )),
    ],
)

__all__ = ["view_conv"]
