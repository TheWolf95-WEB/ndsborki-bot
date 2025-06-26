# conversations/view.py

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
    CallbackContext,
    ContextTypes,
    filters
)
from utils.db import load_db, load_weapon_types
from utils.translators import load_translation_dict, get_type_label_by_key
from utils.permissions import admin_only

# Шаги конверсации
VIEW_CATEGORY_SELECT, VIEW_WEAPON, VIEW_SET_COUNT, VIEW_DISPLAY = range(4)

# Отображаемые категории
RAW_CATEGORIES = {
    "Топовая мета": "🔥 Топовая мета",
    "Мета":       "📈 Мета",
    "Новинки":    "🆕 Новинки"
}

@admin_only
async def view_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Первый шаг: выбор категории."""
    buttons = [[label] for label in RAW_CATEGORIES.values()]
    await update.message.reply_text(
        "📁 Выберите категорию сборки:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return VIEW_CATEGORY_SELECT

async def view_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Второй шаг: после выбора категории показываем тип оружия."""
    text = update.message.text.strip()
    # Находим «ключ» по эмоджи-метке
    category = next((k for k, lbl in RAW_CATEGORIES.items() if lbl == text), None)
    if not category:
        # Если пользователь ввёл что-то лишнее
        buttons = [[lbl] for lbl in RAW_CATEGORIES.values()]
        await update.message.reply_text(
            "❌ Пожалуйста, выберите категорию кнопкой.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
        )
        return VIEW_CATEGORY_SELECT

    context.user_data['selected_category'] = category

    # Из базы берём все сборки
    data = load_db()
    # Фильтруем набор типов по mode=Warzone и категории
    type_keys = sorted({
        b['type']
        for b in data
        if b.get("mode","").lower() == "warzone"
           and b.get("category") == category
    })

    if not type_keys:
        await update.message.reply_text(
            "⚠️ Сборок для этой категории пока нет.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Маппинг key->label из types.json
    key_to_label = {wt['key']: wt['label'] for wt in load_weapon_types()}
    # Обратный маппинг для обработки выбора
    context.user_data['label_to_key'] = {lbl: k for k, lbl in key_to_label.items()}

    buttons = [[key_to_label.get(t, t)] for t in type_keys]
    await update.message.reply_text(
        "➡ Выберите тип оружия:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return VIEW_WEAPON

async def view_select_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Третий шаг: выбор конкретного оружия."""
    label = update.message.text.strip()
    key = context.user_data['label_to_key'].get(label)
    if not key:
        buttons = [[lbl] for lbl in context.user_data['label_to_key'].keys()]
        await update.message.reply_text(
            "❌ Пожалуйста, выберите тип кнопкой.",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
        )
        return VIEW_WEAPON

    context.user_data['selected_type'] = key

    data = load_db()
    weapon_names = sorted({
        b['weapon_name']
        for b in data
        if b['type'] == key
           and b.get('category') == context.user_data['selected_category']
    })

    if not weapon_names:
        await update.message.reply_text(
            "⚠️ Нет сборок для этого типа и категории.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    context.user_data['available_weapons'] = weapon_names
    buttons = [[name] for name in weapon_names]
    await update.message.reply_text(
        "➡ Выберите оружие:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return VIEW_SET_COUNT

async def view_set_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Четвёртый шаг: выбор количества модулей."""
    weapon = update.message.text.strip()
    context.user_data['selected_weapon'] = weapon

    data = load_db()
    key = context.user_data['selected_type']
    # Считаем по 5 и 8 модулей
    count_5 = sum(1 for b in data if b['weapon_name']==weapon and b['type']==key and len(b['modules'])==5)
    count_8 = sum(1 for b in data if b['weapon_name']==weapon and b['type']==key and len(b['modules'])==8)

    # Одна строка с кнопками
    buttons = [[f"5 ({count_5})", f"8 ({count_8})"]]
    await update.message.reply_text(
        "Выберите количество модулей:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)
    )
    return VIEW_DISPLAY

async def view_display_builds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пятый шаг: показываем сборку и навигацию."""
    raw = update.message.text.strip()
    try:
        count = int(raw.split()[0])
    except:
        await update.message.reply_text("⚠️ Нажмите кнопку «5 (...)» или «8 (...)».")
        return VIEW_DISPLAY

    context.user_data['selected_count'] = count
    data = load_db()
    filtered = [
        b for b in data
        if b['type'] == context.user_data['selected_type']
           and b['weapon_name'] == context.user_data['selected_weapon']
           and len(b['modules']) == count
           and b.get('category') == context.user_data['selected_category']
    ]

    if not filtered:
        # Если вдруг нет подходящих (хотя кнопка показывала ноль) — вернёмся к выбору count
        return await view_set_count(update, context)

    context.user_data['viewed_builds'] = filtered
    context.user_data['current_index'] = 0
    return await send_build(update, context)

async def send_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вывод одной сборки по индексу current_index."""
    idx = context.user_data['current_index']
    build = context.user_data['viewed_builds'][idx]
    translation = load_translation_dict(build['type'])

    modules_text = "\n".join(
        f"├ {k}: {translation.get(v, v)}"
        for k, v in build['modules'].items()
    )

    caption = (
        f"📌 <b>Оружие:</b> {build['weapon_name']}\n"
        f"🎯 <b>Дистанция:</b> {build.get('role','-')}\n"
        f"🔫 <b>Тип:</b> {get_type_label_by_key(build['type'])}\n\n"
        f"🧩 <b>Модули:</b> {len(build['modules'])}\n{modules_text}\n\n"
        f"✍ <b>Автор:</b> {build['author']}"
    )

    # Навигация: если есть предыдущая и/или следующая
    nav = []
    row = []
    if idx > 0:
        row.append("⬅ Предыдущая")
    if idx < len(context.user_data['viewed_builds']) - 1:
        row.append("➡ Следующая")
    nav.append(row)
    nav.append(["📋 Сборки Warzone"])

    markup = ReplyKeyboardMarkup(nav, resize_keyboard=True, one_time_keyboard=False)

    img_path = build.get('image')
    if img_path and os.path.exists(img_path):
        with open(img_path, 'rb') as img:
            await update.message.reply_photo(
                photo=InputFile(img),
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

# Собираем ConversationHandler
view_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^📋 Сборки Warzone$"), view_start)
    ],
    states={
        VIEW_CATEGORY_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_category_selected)],
        VIEW_WEAPON:          [MessageHandler(filters.TEXT & ~filters.COMMAND, view_select_weapon)],
        VIEW_SET_COUNT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, view_set_count)],
        VIEW_DISPLAY: [
            MessageHandler(filters.Regex("^[58]"), view_display_builds),
            MessageHandler(filters.Regex("^➡ Следующая$"), next_build),
            MessageHandler(filters.Regex("^⬅ Предыдущая$"), previous_build),
            MessageHandler(filters.Regex("^📋 Сборки Warzone$"), view_start),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u,c: u.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove()))
    ]
)

__all__ = ["view_conv"]
