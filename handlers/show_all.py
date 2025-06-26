# handlers/show_all.py

import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from utils.db import load_weapon_types

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "database", "builds.json")
PAGE_SIZE = 5

CATEGORY_EMOJI = {
    "Топовая мета": "🔥",
    "Мета": "📈",
    "Новинки": "🆕",
}

def load_builds() -> list:
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_type_label_by_key(type_key: str) -> str:
    for item in load_weapon_types():
        if item["key"] == type_key:
            return item["label"]
    return type_key  # если не найдено

def make_categories_keyboard(builds: list) -> InlineKeyboardMarkup:
    counts = {}
    for b in builds:
        counts[b.get("category", "—")] = counts.get(b.get("category", "—"), 0) + 1
    buttons = []
    for cat, emoji in CATEGORY_EMOJI.items():
        cnt = counts.get(cat, 0)
        # каждая кнопка — отдельный список, так что будут друг под другом
        buttons.append([InlineKeyboardButton(f"{emoji} {cat} ({cnt})", callback_data=f"cat|{cat}|0")])
    return InlineKeyboardMarkup(buttons)

def make_page_keyboard(category: str, page: int, total: int) -> InlineKeyboardMarkup:
    kb = []
    if page > 0:
        kb.append(InlineKeyboardButton("⬅ Пред.", callback_data=f"cat|{category}|{page-1}"))
    if (page+1)*PAGE_SIZE < total:
        kb.append(InlineKeyboardButton("След. ➡", callback_data=f"cat|{category}|{page+1}"))
    kb.append(InlineKeyboardButton("🏠 К категориям", callback_data="back|0|0"))
    # Каждая кнопка — на своей строке:
    return InlineKeyboardMarkup([[b] for b in kb])

async def show_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    builds = load_builds()
    total = len(builds)
    text = (
        f"📦 <b>Все сборки</b>\n"
        f"Всего сборок: <b>{total}</b>\n"
        f"ℹ️ Нажмите на нужную категорию, чтобы посмотреть все сборки в ней:"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=make_categories_keyboard(builds)
    )

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]
    builds = load_builds()
    if action == "back":
        total = len(builds)
        text = (
            f"📦 <b>Все сборки</b>\n"
            f"Общее количество сборок в нашей БД: <b>{total}</b>\n\n"
            f"ℹ️ Нажмите на нужную категорию, чтобы посмотреть все сборки в ней:"
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=make_categories_keyboard(builds)
        )
        return

    # Выбрана категория
    category = data[1]
    page = int(data[2])
    filtered = [b for b in builds if b.get("category") == category]
    total_in_cat = len(filtered)
    chunk = filtered[page*PAGE_SIZE:(page+1)*PAGE_SIZE]

    lines = [f"📂 <b>Сборки категории «{category}»</b> (<code>{total_in_cat}</code>)\n"]
    for idx, b in enumerate(chunk, start=page*PAGE_SIZE + 1):
        name = b.get("weapon_name", "—")
        role = b.get("role", "-")
        type_key = b.get("type", "—")
        typ = get_type_label_by_key(type_key)
        cnt = len(b.get("modules", {}))
        auth = b.get("author", "—")

        # модули
        modules_lines = []
        modules = b.get("modules", {})
        for mod, val in modules.items():
            modules_lines.append(f"   └ {mod}: <b>{val}</b>")
        modules_text = "\n".join(modules_lines) if modules_lines else "   └ Нет модулей"

        lines.append(
            f"<b>{idx}. {name}</b>\n"
            f"├ 📏 Дистанция: {role}\n"
            f"├ ⚙️ Тип: {typ}\n"
            f"├ 🔩 Модулей: {cnt}\n"
            f"{modules_text}\n"
            f"└ 👤 Автор: {auth}\n"
        )

    kb = make_page_keyboard(category, page, total_in_cat)
    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=kb
    )

show_all_handler  = CommandHandler("show_all", show_all_command)
show_all_callback = CallbackQueryHandler(category_callback, pattern="^(cat|back)\|")
