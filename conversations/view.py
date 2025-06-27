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
    buttons = [[lbl] for lbl in RAW_CATEGORIES.values()]
    await update.message.reply_text(
        "📁 Выберите категорию сборки:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(lbl, callback_data=f"cat|{key}")]
                                          for key, lbl in RAW_CATEGORIES.items()]),
    )
    return VIEW_CATEGORY_SELECT

async def on_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, category = query.data.split("|", 1)
    context.user_data["selected_category"] = category

    # собираем список типов оружия
    data = load_db()
    type_keys = sorted({
        b["type"] for b in data
        if b.get("mode", "").lower() == "warzone"
           and b.get("category") == category
    })
    if not type_keys:
        return await query.edit_message_text("⚠️ Нет сборок в этой категории.")

    # готовим inline-кнопки типов
    key_to_label = {wt["key"]: wt["label"] for wt in load_weapon_types()}
    buttons = [
        [InlineKeyboardButton(key_to_label.get(k, k), callback_data=f"type|{k}")]
        for k in type_keys
    ]
    await query.edit_message_text(
        "➡ Выберите тип оружия:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return VIEW_WEAPON

async def on_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, type_key = query.data.split("|", 1)
    context.user_data["selected_type"] = type_key

    # собираем список оружия
    weapon_list = sorted({
        b["weapon_name"] for b in load_db()
        if b["type"] == type_key
           and b.get("category") == context.user_data["selected_category"]
    })
    if not weapon_list:
        return await query.edit_message_text("⚠️ По этому типу нет оружия.")

    buttons = [
        [InlineKeyboardButton(w, callback_data=f"weapon|{w}")]
        for w in weapon_list
    ]
    await query.edit_message_text(
        "🔫 Выберите оружие:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return VIEW_SET_COUNT

async def on_weapon_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, weapon = query.data.split("|", 1)
    context.user_data["selected_weapon"] = weapon

    data = load_db()
    c5 = sum(
        1 for b in data
        if b["weapon_name"] == weapon
           and b["type"] == context.user_data["selected_type"]
           and len(b["modules"]) == 5
           and b.get("category") == context.user_data["selected_category"]
    )
    c8 = sum(
        1 for b in data
        if b["weapon_name"] == weapon
           and b["type"] == context.user_data["selected_type"]
           and len(b["modules"]) == 8
           and b.get("category") == context.user_data["selected_category"]
    )

    buttons = [
        [
            InlineKeyboardButton(f"5 модулей ({c5})",
                                  callback_data=f"view|{5}|0"),
            InlineKeyboardButton(f"8 модулей ({c8})",
                                  callback_data=f"view|{8}|0"),
        ]
    ]
    await query.edit_message_text(
        "➡ Выберите количество модулей:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return VIEW_DISPLAY

async def on_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор количества модулей И навигацию «‹›» между сборками.
    callback_data = "view|<count>|<index>"
    """
    query = update.callback_query
    await query.answer()
    _, count_str, idx_str = query.data.split("|")
    count = int(count_str)
    idx = int(idx_str)

    # фильтруем сборки
    filtered = [
        b for b in load_db()
        if b["type"] == context.user_data["selected_type"]
           and b["weapon_name"] == context.user_data["selected_weapon"]
           and len(b["modules"]) == count
           and b.get("category") == context.user_data["selected_category"]
    ]
    if not filtered:
        return await query.edit_message_text("⚠️ Сборок с таким количеством нет.")

    # корректируем idx в случае выхода за пределы
    idx = idx % len(filtered)
    context.user_data["viewed_builds"] = filtered
    context.user_data["current_count"] = count
    context.user_data["current_index"] = idx

    # подготавливаем вывод
    build = filtered[idx]
    translation = load_translation_dict(build["type"])
    modules = "\n".join(
        f"├ {k}: {translation.get(v, v)}"
        for k, v in build["modules"].items()
    )
    caption = (
        f"📌 <b>Оружие:</b> {build['weapon_name']}\n"
        f"🎯 <b>Роль:</b> {build.get('role','-')}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(build['type'])}\n\n"
        f"🧩 <b>Модули ({count}):</b>\n{modules}\n\n"
        f"✍ <b>Автор:</b> {build['author']}"
    )

    # навигационные кнопки
    prev_idx = (idx - 1) % len(filtered)
    next_idx = (idx + 1) % len(filtered)
    nav_buttons = []
    if len(filtered) > 1:
        nav_buttons.append(
            InlineKeyboardButton("⬅ Предыдущая", callback_data=f"view|{count}|{prev_idx}")
        )
        nav_buttons.append(
            InlineKeyboardButton("Следующая ➡", callback_data=f"view|{count}|{next_idx}")
        )

    # кнопка «назад к старту»
    nav_buttons.append(
        InlineKeyboardButton("📋 Категории", callback_data="restart")
    )

    markup = InlineKeyboardMarkup([nav_buttons])

    # отправляем media или текст
    img_path = build.get("image")
    if img_path and pathlib.Path(img_path).exists():
        media = InputMediaPhoto(open(img_path, "rb"), caption=caption, parse_mode="HTML")
        await query.edit_message_media(media=media, reply_markup=markup)
    else:
        await query.edit_message_text(caption, reply_markup=markup, parse_mode="HTML")

    return VIEW_DISPLAY

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
            CallbackQueryHandler(on_weapon_selected, pattern="^weapon\\|"),
        ],
        VIEW_SET_COUNT: [
            # Не используется — переходим сразу в VIEW_DISPLAY после выбора оружия
        ],
        VIEW_DISPLAY: [
            CallbackQueryHandler(on_view_callback, pattern="^view\\|"),
            CallbackQueryHandler(on_restart, pattern="^restart$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: u.callback_query.message.reply_text(
            "❌ Отменено.", reply_markup=None
        )),
    ],
)

__all__ = ["view_conv"]
